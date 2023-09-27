#!/bin/bash
# this command will export all env variables

export $(grep -v '^#' .env | xargs -d '\n')
