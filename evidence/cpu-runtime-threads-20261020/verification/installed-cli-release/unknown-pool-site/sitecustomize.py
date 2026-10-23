import threadpoolctl
original=threadpoolctl.threadpool_info
threadpoolctl.threadpool_info=lambda:original()[:1]
