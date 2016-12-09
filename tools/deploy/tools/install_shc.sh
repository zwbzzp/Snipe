#!/bin/bash

sudo apt-get update
sudo apt-get -y install build-essential

sudo add-apt-repository -y ppa:neurobin/ppa
sudo apt-get update
sudo apt-get -y install shc