spark-submit\
    --master yarn\
    --deploy-mode client\
    --num-executors 3\
    Comp5349-A2.py\
    --output $1
