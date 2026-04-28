[app]
title = Boxing Timer
package.name = boxingtimer
package.domain = org.example

source.dir = .
source.include_exts = py,kv,png,jpg,mp3,wav
source.include_patterns = main.py,static/*.mp3
source.exclude_dirs = android-app,.git,__pycache__,.venv,venv

version = 0.2.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
