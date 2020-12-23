#/bin/bash

over=0
while [ "$over" -eq 0 ]
do
    python3 tunnel.py
    over=$?
done
