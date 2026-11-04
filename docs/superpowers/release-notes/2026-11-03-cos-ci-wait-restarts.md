# 2026-11-03 Chief of Staff stops restarting children that only wait on CI

The Chief of Staff no longer restarts a child whose run shows as finished while it waits on CI or another background command. Re-run `install.sh` in an app to pick it up; nothing else to do. `cos_idle_check.py --wait <PREFIX>-N` is the new check behind it.
