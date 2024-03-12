# Chzzk-downloader

A simple chzzk live stream downloader with python and ffmpeg.

## TODO
- [x] Parse streamer's live status and show it on console.
- [x] Parse Live m3u8
- [x] Download video
- [ ] Refactorize code
- [ ] Save thumbnail
- [ ] Type definition
- [ ] Save chat logs as csv (for manage)
- [ ] Automatically detect stream and start recording
- [ ] Recording multi stream at once
- [ ] GUI support


## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python main.py [-h] [-l LINK] [-u UUID] -o OUTPUT
```

```bash
usage: python main.py [-h] [-l LINK] [-u UUID] -o OUTPUT

원하는 치지직 스트리머의 생방송 영상을 자동으로 녹화하고 저장합니다.

optional arguments:
  -h, --help            show this help message and exit
  -l LINK, --link LINK  스트리머의 생방송 주소를 입력하세요.
  -u UUID, --uuid UUID  스트리머의 uuid를 입력하세요.
  -o OUTPUT, --output OUTPUT
                        녹화된 영상을 저장할 경로를 입력하세요.

mady by @d2n0s4ur
```

## Example
```bash
python main.py -u dfffd9591264f43f4cbe3e2e3252c35c -o .
```


## License
[MIT](https://choosealicense.com/licenses/mit/)


## Author
[@d2n0s4ur](https://github.com/d2n0s4ur)


## Notice
본 파이썬 프로그램은 치지직 생방송을 녹화하고 저장하는 프로그램입니다.

동영상을 녹화하고 공유하는 행위는 저작권자의 동의를 받아야하며, 이 프로그램을 사용하여 생방송 영상을 녹화를 하거나 공유하는 행위에 대한 책임은 사용자에게 있습니다.
