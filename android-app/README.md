# Android APK (Boxing Timer)

Это Android-проект (WebView-оболочка), который запускает таймер из вашего скрипта как локальную HTML/JS-страницу.

## Как собрать APK

1. Установите Android Studio (или Android SDK + JDK 17).
2. Откройте папку `android-app` как проект Gradle.
3. Дождитесь sync.
4. Соберите debug APK:
   - Android Studio: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - или командой: `./gradlew :app:assembleDebug`
5. Готовый файл:
   `app/build/outputs/apk/debug/app-debug.apk`

### Если ошибка по Java/toolchain

Перед сборкой выставьте совместимую Java (рекомендуется JDK 17):

```bash
export JAVA_HOME=/path/to/jdk-17
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```


## Что внутри

- `app/src/main/assets/index.html` — адаптированная версия таймера.
- Звук генерируется через Web Audio API (без отдельных бинарных mp3-файлов).
- `MainActivity.kt` — запуск локальной страницы в `WebView`.

## Важно

- На Android Wake Lock API из браузера может работать ограниченно в WebView.
- Звук в некоторых прошивках может требовать первый явный тап пользователя (кнопка СТАРТ).
