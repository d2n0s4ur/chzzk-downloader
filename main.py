# -*- coding: utf-8 -*-
import argparse
import re
import requests
import time
import json
import ffmpeg
import os

################ REGEX ################
chzzk_url_regex = r'^https:\/\/chzzk.naver.com\/live\/[a-z0-9]*$'
chzzk_uuid_regex = r'[a-z0-9]*$'

################ VARIABLES ################
chzzk_uuid = ''
live_info = {
  'liveTitle': '',
  'status': '',
  'concurrentUserCount': 0,
  'accumulateCount': 0,
  'paidPromotion': False,
  'adult': False,
  'chatChannelId': '',
  'categoryType': '',
  'liveCategory': '',
  'liveCategoryValue': '',
  'openDate': '',
  'liveImageUrl': '',
  'liveId': 0,
  'channelName': '',
}
live_playback_json = {}
hls_encoding_path = ''
llhls_encoding_path = ''
encoding_data = []
fragment_m3u8 = ''

# Convert time string to uptime (seconds)
def get_uptime(start_date):
  start_date = time.strptime(start_date, '%Y-%m-%d %H:%M:%S')
  start_date = time.mktime(start_date)
  current_date = time.time()
  uptime = current_date - start_date
  return uptime

def get_live_info(channel):
  global live_playback_json
  url = f'https://api.chzzk.naver.com/service/v2/channels/{channel}/live-detail'
  
  # request headers
  request_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Referer': f'https://chzzk.naver.com/live/{channel}'
  }
  # set request headers
  response = requests.get(url, headers=request_headers)
  data = response.json()
  
  # check status code
  if response.status_code != 200:
    print(f'Error: {response.status_code}')
    exit(1)
  content = data['content']

  # save live info
  live_info['liveTitle'] = content['liveTitle']
  live_info['status'] = content['status']
  live_info['concurrentUserCount'] = content['concurrentUserCount']
  live_info['accumulateCount'] = content['accumulateCount']
  live_info['paidPromotion'] = content['paidPromotion']
  live_info['adult'] = content['adult']
  live_info['chatChannelId'] = content['chatChannelId']
  live_info['categoryType'] = content['categoryType']
  live_info['liveCategory'] = content['liveCategory']
  live_info['liveCategoryValue'] = content['liveCategoryValue']
  live_info['openDate'] = content['openDate']
  live_info['liveImageUrl'] = content['liveImageUrl']
  live_info['liveId'] = content['liveId']
  live_info['channelName'] = content['channel']['channelName']
  live_playback_json = json.loads(content['livePlaybackJson'])
  
  return live_info['status'] == 'OPEN'

def print_live_info(live_info):
  uptime = get_uptime(live_info['openDate'])
  
  print('생방송을 찾았습니다.')
  print(f'생방송 제목: {live_info["liveTitle"]}')
  print(f'카테고리: {live_info["liveCategoryValue"]}')
  print(f'동시 시청자 수: {live_info["concurrentUserCount"]}')
  print('업타임: {0:02d}:{1:02d}:{2:02d}\n'.format(int(uptime // 3600), int(uptime % 3600 // 60), int(uptime % 60)))

def print_hls_list(live_playback_json):
  global hls_encoding_path
  for media in live_playback_json['media']:
    if media['mediaId'] == 'HLS' and media['protocol'] == 'HLS' and media['path'] != '':
      hls_encoding_path = media['path']
      print('HLS Encoding')
      for i, track in enumerate(media['encodingTrack']):
        if track['encodingTrackId'] == 'alow.stream':
          continue
        print('({0}) {1: >5} {2: >6}K {3}fps {4}x{5}'.format(i + 1, track['encodingTrackId'], int(track['videoBitRate'] / 1000), track['videoFrameRate'], track['videoWidth'], track['videoHeight']))
        encoding_data.append({
          'encodingTrackId': track['encodingTrackId'],
          'videoBitRate': int(track['videoBitRate']),
          'videoFrameRate': track['videoFrameRate'],
          'videoWidth': track['videoWidth'],
          'videoHeight': track['videoHeight'],
          'videoProfile': track['videoProfile'],
          'audioProfile': track['audioProfile'],
        })
      print()

def ft_parse_m3u8(m3u8, encoding_info, channel=chzzk_uuid):
  print('request m3u8...')
  request_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Referer': f'https://chzzk.naver.com/live/{channel}'
  }
  response = requests.get(m3u8, headers=request_headers)
  
  m3u8_content = response.text
  m3u8_content = m3u8_content.split('\n')
  m3u8_content = list(filter(lambda x: x != '', m3u8_content))
  m3u8_content = list(filter(lambda x: x[0] != '#', m3u8_content))
  for line in m3u8_content:
    if line.find(encoding_info['encodingTrackId']) != -1:
      fragment_m3u8 = hls_encoding_path.split('hls_playlist')[0] + line

  if fragment_m3u8 == '' :
    print('get m3u8 failed')
    exit(1)
  print('get m3u8 success')
  return fragment_m3u8

def record_with_ffmpeg(output_path):
  global fragment_m3u8
  global live_info
  
  vfrag_input = ffmpeg.input(fragment_m3u8)
  output_file = f'{output_path}/[{live_info["openDate"]}] {live_info["channelName"]} - {live_info["liveTitle"]}.ts'
  output = ffmpeg.output(vfrag_input, output_file, vcodec='copy', acodec='copy')
  
  # run ffmpeg command in other process
  ffmpeg.run(output, quiet=True, capture_stdout=True, capture_stderr=True)
  

def record(output_path):
  global fragment_m3u8
  global chzzk_uuid
  global live_info
  output_tmp_dir = f'{output_path}/tmp/{live_info["liveId"]} - {live_info["channelName"]}'
  stored_fragment = []
  fail_count = 0
  # output_file = f'[{live_info["openDate"]}] {live_info["channelName"]} - {live_info["liveTitle"]}.ts'
  # create tmp directory
  try:
    os.mkdir(f'{output_tmp_dir}')
  except FileExistsError:
    pass
  
  print('recording start...')
  response = requests.get(fragment_m3u8, timeout=10)
  m3u8_content = response.text
  m3u8_content = m3u8_content.split('\n')
  m3u8_content = list(filter(lambda x: x != '', m3u8_content))
  for line in m3u8_content:
    if line.find('#EXT-X-MAP:URI') != -1:
      m4s_url = fragment_m3u8.split('hls_chunklist')[0] + line.split('URI="')[1].split('"')[0]
      m4s_res = requests.get(m4s_url, timeout=5)
      with open(f'{output_tmp_dir}/1080p_0_0_0.m4s', 'wb') as f:
        f.write(m4s_res.content)
      break
  
  while fail_count < 15:
    response = requests.get(fragment_m3u8, timeout=10)
    m3u8_content = response.text
    m3u8_content = m3u8_content.split('\n')
    m3u8_content = list(filter(lambda x: x != '', m3u8_content))
    fragments = list(filter(lambda x: x[0] != '#', m3u8_content))
    for fragment in fragments:
      if fragment not in stored_fragment:
        stored_fragment.append(fragment)
        fragment_url = fragment_m3u8.split('hls_chunklist')[0] + fragment
        # print(fragment_url)
        headers = {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
          'Referer': f'https://chzzk.naver.com/live/{chzzk_uuid}'
        }
        fragment_data = requests.get(fragment_url, timeout=5, headers=headers)
        
        if fragment_data.status_code != 200:
          fail_count += 1
          print(f'Failed to get fragment data. Fail count: {fail_count}')
          continue
        fail_count = 0
        # append fragment data to file
        with open(f'{output_tmp_dir}/{fragment.split("/")[-1].split("?")[0]}', 'wb') as f:
          f.write(fragment_data.content)
      if len(stored_fragment) > 15:
        stored_fragment.pop(0)
    
    # sleep
    time.sleep(2)

  

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
      prog='python main.py',
      description='원하는 치지직 스트리머의 생방송 영상을 자동으로 녹화하고 저장합니다.',
      epilog='mady by @d2n0s4ur'
    )
    
    parser.add_argument('-l', '--link', type=str, help='스트리머의 생방송 주소를 입력하세요.', required=False)
    parser.add_argument('-u', '--uuid', type=str, help='스트리머의 uuid를 입력하세요.', required=False)
    parser.add_argument('-o', '--output', type=str, help='녹화된 영상을 저장할 경로를 입력하세요.', required=False)
    args = parser.parse_args()
    
    # check args
    if not args.link and not args.uuid:
        print('스트리머의 생방송 주소 또는 uuid를 입력하세요.')
        exit(1)
    
    if args.uuid:
        if not re.match(chzzk_uuid_regex, args.uuid):
            print('올바른 uuid를 입력하세요.')
            exit(1)
        chzzk_uuid = args.uuid
    if args.link:
        if not re.match(chzzk_url_regex, args.link):
            print('올바른 생방송 주소를 입력하세요.')
            exit(1)
        chzzk_uuid = re.findall(chzzk_uuid_regex, args.link)[0]

    if not get_live_info(chzzk_uuid):
        print('생방송 중인 채널이 아닙니다. 인자를 다시 확인하세요.')
        exit(1)
    
    print_live_info(live_info)
    print_hls_list(live_playback_json)
    print('녹화를 중단하기 위해서는 Ctrl + C를 누르세요.')
    print('원하는 화질을 선택하세요: ', end='')
    selected_encoding = int(input())
    
    # check selected encoding
    if selected_encoding < 1 or selected_encoding > len(encoding_data):
        print('올바른 화질을 선택하세요.')
        exit(1)
    
    # start recording
    print(f'녹화를 시작합니다. 선택한 화질: {encoding_data[selected_encoding - 1]["encodingTrackId"]}')
    fragment_m3u8 = ft_parse_m3u8(hls_encoding_path, encoding_data[selected_encoding - 1])
    print(fragment_m3u8)
    record(args.output if args.output else '.')
    
    print('녹화가 완료되었습니다.')
    print('다운받은 영상을 mp4로 변환하시겠습니까? (y/n): ', end='')
    convert = input()
    
    if convert == 'y':
      print('변환 중...')
      input_file = f'{args.output}/[{live_info["openDate"]}] {live_info["channelName"]} - {live_info["liveTitle"]}.ts'
      output_file = f'{args.output}/[{live_info["openDate"]}] {live_info["channelName"]} - {live_info["liveTitle"]}.mp4'
      ffmpeg.input(input_file).output(output_file).run(quiet=True, capture_stdout=True, capture_stderr=True)
      print('변환 완료')
    else:
      print('프로그램을 종료합니다.')
      exit(0)