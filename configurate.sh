#!/bin/bash

if [ ! -d "cartola" ]; then
    python3 -m venv cartola

    source cartola/bin/activate

    pip install requests pandas
fi