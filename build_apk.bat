@echo off
set JAVA_HOME=C:\Users\issda\jdk-21\jdk-21.0.10
set ANDROID_HOME=C:\Users\issda\android-sdk
set PATH=%PATH%;C:\Program Files\nodejs;%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools
cd kindle-app\android
gradlew.bat assembleDebug