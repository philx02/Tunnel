import time

count = 0
while True:
    print(count)
    count += 1
    if count > 9:
        count = 0
    time.sleep(1)