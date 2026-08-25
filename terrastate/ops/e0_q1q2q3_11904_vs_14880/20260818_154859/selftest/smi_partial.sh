#!/bin/bash
case "$*" in
  *compute-apps*) exit 0 ;;
  *index,memory.used,utilization.gpu*) echo "0, 4, 0"; echo "1, 4, 0"; echo "2, 4, 0"; for i in 3 4 5 6 7; do echo "$i, 78000, 88"; done ;;
esac
