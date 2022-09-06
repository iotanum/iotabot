#!/bin/bash

sudo -E docker-compose up --build -d
sudo -E docker system prune -f
