spark-submit \
    --master yarn\
    --deploy-mode client \
    --num-executors 3 \
    comp5349-assignment2.py \
    --output $1