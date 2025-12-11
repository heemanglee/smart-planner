#!/bin/bash

uvicorn app.api.main:app --reload --port 8001
