import pyautogui
import time

# Небольшая пауза, чтобы пользователь успел переключить внимание на экран
time.sleep(1)

# Определяем текущую позицию
start_x, start_y = pyautogui.position()

# Двигаем мышку вправо-влево несколько раз
for i in range(3):
    # Вправо
    pyautogui.moveTo(start_x + 200, start_y, duration=0.5)
    # Влево
    pyautogui.moveTo(start_x - 200, start_y, duration=0.5)

# Возвращаемся в исходную точку
pyautogui.moveTo(start_x, start_y, duration=0.5)
