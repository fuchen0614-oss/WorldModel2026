#!/bin/bash
case "$*" in
  *compute-apps*) exit 0 ;;
  *index,memory.used,utilization.gpu*) for i in 0 1 2 3 4 5 6 7; do echo "$i, 4, 0"; done ;;
esac
