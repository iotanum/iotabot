#/bin/bash

sudo docker-compose up --build -d
sudo docker image prune -f
sudo docker container prune -f