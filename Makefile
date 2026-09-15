.DEFAULT_GOAL := make

.PHONY: make debug-cycle check-space

MIN_FREE_KB := 5242880
FREE_KB := $(shell df -Pk . | awk 'NR == 2 { print $$4 }')

# Не починати збірку, якщо системі не залишається запас у 5 ГіБ.
check-space:
	@echo "Вільно на диску: $$(( $(FREE_KB) / 1024 / 1024 )) ГіБ; мінімальний запас: 5 ГіБ"
	@test "$(FREE_KB)" -ge "$(MIN_FREE_KB)"

# Збирає release APK, встановлює та запускає застосунок на підключеному пристрої.
make: check-space
	./gradlew :app:assembleRelease
	adb install -r app/build/outputs/apk/release/app-release.apk
	adb shell am start -W -n com.agent008/.MainActivity

# Швидкий цикл розробки: debug APK, встановлення та запуск на пристрої.
debug-cycle: check-space
	./gradlew :app:assembleDebug
	adb install -r app/build/outputs/apk/debug/app-debug.apk
	adb shell am start -W -n com.agent008/.MainActivity
