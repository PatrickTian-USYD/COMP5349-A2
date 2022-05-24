from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql import Row

"""**Segment**

Overlap
"""
def if_overlap(range_of_answer, range_of_sequence):
  if range_of_answer[0]>range_of_sequence[1] or range_of_answer[1]<range_of_sequence[0]:
    return False
  else:
    return True

def constructor(title, sequence, question, answer_start, answer_end, mark):
  Con = []
  Con.append(title)
  Con.append(sequence)
  Con.append(question)
  Con.append(answer_start)
  Con.append(answer_end)
  Con.append(mark)
  return tuple(Con)

"""Segment"""

def Segment(Contract):
  title = Contract[0]
  content = Contract[1][0]
  range_of_content = [0, len(content)-1]
  qas = Contract[1][1]

  number_of_PNS = 0
  number_of_PS = 0
  Cons = []
  number_of_seq = int(len(content)/2048)+1
  for i in range(number_of_seq):
    start_of_seq = i * 2048
    len_of_seq = min(len(content)-start_of_seq, 4096)
    end_of_seq = start_of_seq + len_of_seq   #range of sequence
    Seq = content[start_of_seq: end_of_seq]
    PS = False
    for Q in qas:
      if Q[2] is True:
        Con = constructor(title, Seq, Q[3], 0, 0, "INS")  #INS
        Cons.append(Con)
      else:
        Seq_samples = []
        for answer in Q[0]:
          range_of_answer = [answer[0], answer[0] + len(answer[1])]
          if if_overlap(range_of_answer, [start_of_seq, end_of_seq -1]):
            number_of_PS += 1   #PS
            Con = constructor(title, Seq, Q[3], range_of_answer[0], range_of_answer[1], "PS")
            Seq_samples.append(Con)
            PS = True
          elif number_of_PNS >= number_of_PS or PS:
            continue
          else:
            number_of_PNS += 1   #PNS
            Con = constructor(title, Seq, Q[3], range_of_answer[0], range_of_answer[1], "PNS")
            Seq_samples.append(Con)
        Cons.extend(Seq_samples)
  return Cons

def Constructor_2(title, sequence, questions, start_of_answer, end_of_answer, mark):
  Con_2 = []
  Con_2.append(sequence)
  Con_2.append(questions)
  Con_2.append(start_of_answer)
  Con_2.append(end_of_answer)
  return tuple(Con_2)

def ins_filtering(contract):
  title = contract[0]
  limit = -1
  count = 0
  Sample = []

  for sequence in contract[1]:
    if limit == -1:
      total_of_ps = 0
      number_of_contract = 0
      for count_of_ps in sequence[0]:
        if count_of_ps[0] != title and count_of_ps[1] > 0:
          total_of_ps += count_of_ps[1]
          number_of_contract += 1
      limit = int(total_of_ps/number_of_contract)

    if sequence[5] == "INS":
      if count >= limit:
        continue
      else:
        count += 1

    sample = Constructor_2(title, sequence[1], sequence[2], sequence[3], sequence[4], sequence[5])
    Sample.append(sample)
  return Sample


spark = SparkSession \
    .builder \
    .appName("COMP5349 A2 ") \
    .config("spark.sql.shuffle.partitions", 10)\
    .config("spark.executor.cores", '4')\
    .config("spark.executor.memory", '2g')\
    .config("dynamicAllocation.MaxExecutors", 10)\
    .getOrCreate()

"""Load dataset"""

test_data = "test.json"
test_df_1 = spark.read.json(test_data)

"""**Assignment 2**

Extracting data from 鈥渄ata鈥?"""

T_df = test_df_1.select((explode("data").alias('data')))

"""Remove the data, keep the title and paragraph"""

T_rdd = T_df.rdd.map(lambda x: (x[0][1], x[0][0]))
test_df_2 = spark.createDataFrame(T_rdd.map(lambda x: Row(title=x[0], paragraphs = x[1])))

"""Expand paragraph content"""

test_df_2 = test_df_2.withColumn('Paragraph',explode('paragraphs')).drop('paragraphs')

test_sample_rdd = test_df_2.rdd.flatMap(Segment).cache()

"""positive samples"""

positive_samples_rdd = test_sample_rdd.filter(lambda x: x[5]=="PS")\
                    .map(lambda x:((x[0], x[2]),1))\
                    .reduceByKey(lambda x,y: x+y)\
                    .map(lambda x: (x[0][1], (x[0][0],x[1])))\
                    .groupByKey()

"""impossible negative sample"""

test_total_rdd = test_sample_rdd.map(lambda x: (x[2], (x[0],x[1],x[3],x[4],x[5])))\
                  .join(positive_samples_rdd)\
                  .map(lambda x: (x[0],x[1][0],x[1][1]))\
                  .map(lambda x: (x[1][0], (x[2], x[1][1], x[0], x[1][2], x[1][3], x[1][4])))\
                  .groupByKey()

Final_sample_RDD = test_total_rdd.flatMap(ins_filtering)

FS = spark.createDataFrame(Final_sample_RDD, ['source','question','answer_start','answer_end'])

#FS.show(20)

FS.write.json("FS.json")