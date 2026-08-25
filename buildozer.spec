[app]
title = MARD拼豆图纸
package.name = mardbead
package.domain = org.mardbead
source.dir = .
source.include_exts = py,json,png,jpg,jpeg,webp,txt
version = 0.4.2
requirements = python3,kivy==2.3.0,pillow
orientation = portrait
fullscreen = 0
android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
