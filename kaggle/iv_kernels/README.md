# Edition-IV member builds on Kaggle (2026-08-19)

The heavy members of the edition-IV stack were built on Kaggle rather than the laptop, sharded across the pool's
four accounts: `kernel_job.py` is the kernel (one shard per kernel; `AQ_JOB=trad` with `AQ_MODULES=` for the
tradition modules, `AQ_JOB=sid` with `AQ_SHARD=k/N` for the PyJHora/iztro features), `launch.py` pushes the shards
round-robin across the accounts (GPU for the tradition fits — XGBoost on CUDA via `AQ_GPU=1` — CPU for the
feature builds, which need no GPU and sit outside the 2-session GPU cap), `sched.py` re-pushes shards refused for
capacity, `collect.py` downloads completed outputs and DISCARDS the 70 MB code copy each kernel drags along (the
first pass filled the disk). The code + data live in the public dataset `artafather/artamatch-iv-code`.
Two traps met: `/kaggle/input/<slug>` for a user dataset; `nvidia-smi` is absent on CPU kernels (guard with
`shutil.which`). Outputs are merged by `build_sidereal.py --merge N` and consumed by `sidereal_members.py` /
`artamodel_iv_ensemble.py` (`AQ_EXTRA=`).
