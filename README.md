# py-image-storage

## What is this?

This is an application, which keep your image files to be small file sized. I build this application for my home-made server (ODROID N2+, Ubuntu 22.04).

## How it works?

This application is using 'Pillow' library to compress image files. It will compress image files in the source path and save them to the destination path. If the destination path is not exist, it will create it automatically. The original file will be deleted. 

It keeps observing the source path, if there is a new image file, it will compress it and save it to the destination path while it is running.

## Why did you build this?

Google Photos no longer provide unlimited storage for free, and I was bored.

---

## How to use.

### 0. Prerequisites

- python3.11
- pip3
- virtualenv

You need to install more libraries, which are in the 'requirements.txt' file, after you create virtual environment and activate it.

### 1. Install python3.11, pip3 and virtualenv (if you don't have them)

```shell
sudo apt-get -y install python3.11 python3-pip virtualenv
# you probably use yum or something else. you would know.
```

### 2. Clone this repository and create virtual environment

```shell
git clone https://github.com/pjc1991/py-image-storage.git
cd py-image-storage
/usr/bin/python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install requirements

```shell
pip3 install -r requirements.txt
```

### 4. Create '.env' file and edit it

```shell
touch .env && vi .env
```

```shell
# .env
UNCOMPRESSED=\\NAS\FILES\uncompressed # uncompressed image files path, source path
COMPRESSED=\\NAS\FILES\compressed # compressed image files path, destination path
```

### 5. Run application

```shell
nohup python -u observer.py &
tail -f nohup.out
```

## How to stop application

```shell
ps -ef | grep observer.py
kill -9 <pid>
```
Sorry, I didn't make a script for this.

---
## More Things to do ~

- [X] Implement async I/O
- [ ] Better performance and structures for async I/O
- [ ] Make a script for stopping application
- [ ] Make this application as a service (systemd)
- [ ] Make a script for installation (not sure if it is necessary

## Tested environment

I tested this application on Ubuntu 22.04 (Odroid N2+) & Windows 11(My gaming desktop). 
Well, It was fast as the file transfer speed of my server, at least.
