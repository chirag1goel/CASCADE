#!/usr/bin/env python
import pickle
import tensorflow as tf
import numpy as np
import os
import time
import datetime
import data_helpers
import sys
from text_cnn import TextCNN
import os
from tensorflow.contrib import learn
import csv
from time import sleep
import pickle



#####################  GPU Configs  #################################

# Selecting the GPU to work on
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="1"

# Desired graphics card config
session_conf = tf.ConfigProto(
      allow_soft_placement=True,
      log_device_placement=False,
      gpu_options=tf.GPUOptions(allow_growth=True))

# Parameters
# ==================================================
np.random.seed(10)


# Data loading params
tf.flags.DEFINE_float("dev_sample_percentage", .1, "Percentage of the training data to use for validation")

# Model Hyperparameters
tf.flags.DEFINE_integer("embedding_dim", 300, "Dimensionality of character embedding (default: 128)")
tf.flags.DEFINE_string("filter_sizes", "3,4,5", "Comma-separated filter sizes (default: '3,4,5')")
tf.flags.DEFINE_integer("num_filters", 128, "Number of filters per filter size (default: 128)")
tf.flags.DEFINE_float("dropout_keep_prob", 0.5, "Dropout keep probability (default: 0.5)")
tf.flags.DEFINE_float("l2_reg_lambda", 0.5, "L2 regularization lambda (default: 0.0)")

# Training parameters
tf.flags.DEFINE_integer("batch_size", 4096, "Batch Size (default: 64)")
tf.flags.DEFINE_integer("num_epochs", 100, "Number of training epochs (default: 200)")
tf.flags.DEFINE_integer("evaluate_every", 100, "Evaluate model on dev set after this many steps (default: 100)")
tf.flags.DEFINE_integer("checkpoint_every", 100, "Save model after this many steps (default: 100)")
tf.flags.DEFINE_integer("num_checkpoints", 5, "Number of checkpoints to store (default: 5)")
# Misc Parameters
tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")

FLAGS = tf.flags.FLAGS

print("loading data...")
x = pickle.load(open("./mainbalancedpickle.p","rb"))
revs, W, W2, word_idx_map, vocab, max_l = x[0], x[1], x[2], x[3], x[4], x[5]
print("data loaded!")# Load data

print('loading wgcca embeddings...')
wgcca_embeddings = np.load('./../users/user_embeddings/user_gcca_embeddings_custom.npz')
print('wgcca embeddings loaded')


ids = np.concatenate((np.array(["unknown"]), wgcca_embeddings['ids']), axis=0)
user_embeddings = wgcca_embeddings['G']
unknown_vector = np.random.normal(size=(1,100))
user_embeddings = np.concatenate((unknown_vector, user_embeddings), axis=0)
user_embeddings = user_embeddings.astype(dtype='float32')

user_embeddings = np.concatenate([user_embeddings,np.tile(unknown_vector,(283396,1))])

# for i in range(92):
# 	user_embeddings = np.concatenate((user_embeddings,unknown_vector), axis=0)

#283592
#283492


# 283592

# for i in range(283492):
# 	user_embeddings = np.concatenate((user_embeddings,unknown_vector), axis=0)

wgcca_dict = {}
for i in range(len(ids)):
    wgcca_dict[ids[i]] = int(i)

csv_reader = csv.reader(open("./../discourse/discourse_features/discourse.csv"))
topic_embeddings = []
topic_ids = []
for line in csv_reader:
    topic_ids.append(line[0])
    topic_embeddings.append(line[1:])
topic_embeddings = np.asarray(topic_embeddings)
topic_embeddings_size = len(topic_embeddings[0])
topic_embeddings = topic_embeddings.astype(dtype='float32')
print("topic emb size: ",topic_embeddings_size)


#3817 - politics


topics_dict = {}
for i in range(len(topic_ids)):
    try:
        topics_dict[topic_ids[i]] = int(i)
    except TypeError:
        print(i)


x_test = []
author_text_id = []
topic_text_id = []
ids = []
with open('../data/custom_data.csv', newline='') as csvfile:
	for row in csv.reader((line.replace('\0','') for line in csvfile), delimiter=","):
	# for row in reader:
		x_test.append(row[0])
		ids.append(row[10])
		try:
			author_text_id.append(wgcca_dict['"'+row[2]+'"'])
		except KeyError:
			author_text_id.append(0)
		try:
			topic_text_id.append(topics_dict["uspolitics"])
		except KeyError:
			topic_text_id.append(0)


y = []
for i in range(len(revs)):
    if revs[i]['split']==1:
        temp_y = revs[i]['label']
        y.append(temp_y)

y = np.asarray(y)

shuffle_indices = np.random.permutation(np.arange(len(y)))
y_shuffled = y[shuffle_indices]
dev_sample_index = -1 * int(FLAGS.dev_sample_percentage * float(len(y)))
y_train, y_dev = y_shuffled[:dev_sample_index], y_shuffled[dev_sample_index:]

# cnn = TextCNN(sequence_length=max_l,num_classes=len(y_train[0]) ,vocab_size=len(vocab),word2vec_W = W,word_idx_map = word_idx_map,user_embeddings = user_embeddings,topic_embeddings = topic_embeddings,embedding_size=FLAGS.embedding_dim,batch_size=FLAGS.batch_size,filter_sizes=list(map(int, FLAGS.filter_sizes.split(","))),num_filters=FLAGS.num_filters,l2_reg_lambda=FLAGS.l2_reg_lambda)


# y_temp = y_dev[:len(x_test)]
# x_test = x_test[:500]
x = []
# max_l = 0
for i in range(len(x_test)):
	a = []
	for word in x_test[i].split():
		if(word in word_idx_map):
			a.append(word_idx_map[word])
		else:
			a.append(0)
	x.append(np.asarray(a))

# padding
for i in range(len(x)):
    if( len(x[i]) < max_l ):
    	x[i] = np.append(x[i],np.zeros(max_l-len(x[i])))		
    elif( len(x[i]) > max_l ):
    	x[i] = x[i][0:max_l]
x = np.asarray(x)

topic_test = np.asarray(topic_text_id)
author_test = np.asarray(author_text_id)

# topic_test = topic_test[:500]
# author_test = author_test[:500]


# print(topic_test)
# print(author_test)

def softmax(x):
	return np.exp(x) / np.sum(np.exp(x), axis=0)

checkpoint_file = tf.train.latest_checkpoint('./models/')
graph = tf.Graph()
with graph.as_default():
    session_conf = tf.ConfigProto(
      allow_soft_placement=True,
      log_device_placement=False)
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        # Load the saved meta graph and restore variables
        # saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
        saver = tf.train.import_meta_graph('./models/main_balanced_user_plus_topic-1.meta')
        saver.restore(sess, checkpoint_file)

        # Get the placeholders from the graph by name
        input_x = graph.get_operation_by_name("input_x").outputs[0]
        input_author = graph.get_operation_by_name("input_author").outputs[0]
        input_topic = graph.get_operation_by_name("input_topic").outputs[0]
        input_topic = graph.get_operation_by_name("input_topic").outputs[0]
        user_w = graph.get_operation_by_name("embedding/user_W").outputs[0]
        # input_y = graph.get_operation_by_name("input_y").outputs[0]
        dropout_keep_prob = graph.get_operation_by_name("dropout_keep_prob").outputs[0]

        # Tensors we want to evaluate
        predictions = graph.get_operation_by_name("output/predictions").outputs[0]
        scores = graph.get_operation_by_name("output/scores").outputs[0]

        # Generate batches for one epoch
        batches = data_helpers.batch_iter_dev(list(x_test), 4096)
        # test_batches = data_helpers.batch_iter_dev(list(zip(x_test, author_test, topic_test)), 64)
        length = len(x_test)

        all_predictions = []
        scores_all = []
        with open("results.csv", 'w') as output_file:
        	writer = csv.writer(output_file)

        	print("going to start writing")
        	for i,batch in enumerate(batches):
        	# for i in range(int(len(x)/64)+1):
        		#if (batch[1]%6400 == 0):
        		print("batch number: " + str(i) + " of " + str(len(batches)))
        		feed_dict = {input_x: x[batch[0]:batch[1]],input_author: author_test[batch[0]:batch[1]],input_topic: topic_test[batch[0]:batch[1]],dropout_keep_prob: 1, user_w: user_embeddings}
        		scores_list,predictions_list = sess.run([scores,predictions], feed_dict)
        		for i in range(batch[1]-batch[0]):
       				writeStr = ""
        			writeStr += str(ids[batch[0]+i]) + ","
        			writeStr += str(scores_list[i][0]) + ","
       				writeStr += str(scores_list[i][1]) + ","
        			writeStr += str(predictions_list[i]) + ","
        			softmaxValues = softmax(np.array([scores_list[i][0],scores_list[i][1]]))
        			writeStr += str(softmaxValues[0]) + ","
        			writeStr += str(softmaxValues[1])
        			#writeStr += "\"" + str(x_test[batch[0]+i]) + "\"" + ","
       				# for ind in range(len(x[i])):
        			#writeStr += np.array2string(W[x[i].astype(int)], formatter={'float_kind':lambda x: "%.8f" % x}, separator=",")
        			writer.writerows([writeStr.split(',')])
        	print("finished writing")
        # all_predictions = np.concatenate([all_predictions, predictions_list])
        # scores_all = np.concatenate([scores_all, scores_list])

            # x_dev_batch = x_dev[dev_batch[0]:dev_batch[1]]
            # author_dev_batch = author_dev[dev_batch[0]:dev_batch[1]]
            # topic_dev_batch = topic_dev[dev_batch[0]:dev_batch[1]]
            # y_dev_batch = y_dev[dev_batch[0]:dev_batch[1]]
            # a, b = dev_step(x_dev_batch, author_dev_batch, topic_dev_batch, y_dev_batch)
            # dev_loss.append(a)
            # conf_mat += b

        # Collect the predictions here
        
        
        # scores,predictions = sess.run([scores,predictions], feed_dict)
        # for x_test_batch in batches:
        #     batch_predictions = sess.run(predictions, {input_x: x_test_batch, dropout_keep_prob: 1.0})
            # all_predictions = np.concatenate([all_predictions, batch_predictions])
        # print("PREDICTIONS -----")
        # print(predictions_list)
        # print("SCORES -----")
        # print(scores_list)

# sess=tf.Session()    
# #First let's load meta graph and restore weights
# saver = tf.train.import_meta_graph('./models/main_balanced_user_plus_topic-1.meta')
# saver.restore(sess,tf.train.latest_checkpoint('./models/'))

# feed_dict = {
# 	cnn.input_x: x,
# 	cnn.input_author: author_test,
# 	cnn.input_topic: topic_test,
# 	cnn.input_y: y_temp,
#   	cnn.dropout_keep_prob: FLAGS.dropout_keep_prob
# }

# predictions, scores = sess.run([cnn.predictions,cnn.scores],feed_dict)
# print("PREDICTIONS -----")
# print(predictions)
# print("SCORES -----")
# print(scores)










# topics_dict = {}
# for i in range(len(topic_ids)):
#     try:
#         topics_dict[topic_ids[i]] = int(i)
#     except TypeError:
#         print(i)

# max_l = 100

# x_text = []
# author_text_id = []
# topic_text_id = []
# y = []

# test_x = []
# test_topic = []
# test_author = []
# test_y = []

# for i in range(len(revs)):
#     if revs[i]['split']==1:
#         x_text.append(revs[i]['text'])
#         try:
#             author_text_id.append(wgcca_dict['"'+revs[i]['author']+'"'])
#         except KeyError:
#             author_text_id.append(0)
#         try:
#             topic_text_id.append(topics_dict['"'+revs[i]['topic']+'"'])
#         except KeyError:
#             topic_text_id.append(0)
#         temp_y = revs[i]['label']
#         y.append(temp_y)
#     else:
#         test_x.append(revs[i]['text'])
#         try:
#             test_author.append(wgcca_dict['"'+revs[i]['author']+'"'])
#         except:
#             test_author.append(0)
#         try:
#             test_topic.append(topics_dict['"'+revs[i]['topic']+'"'])
#         except:
#             test_topic.append(0)
#         test_y.append(revs[i]['label'])  

# y = np.asarray(y)
# test_y = np.asarray(test_y)

# # get word indices
# x = []
# for i in range(len(x_text)):
# 	x.append(np.asarray([word_idx_map[word] for word in x_text[i].split()]))
    
# x_test = []
# for i in range(len(test_x)):
#     x_test.append(np.asarray([word_idx_map[word] for word in test_x[i].split()]))

# # padding
# for i in range(len(x)):
#     if( len(x[i]) < max_l ):
#     	x[i] = np.append(x[i],np.zeros(max_l-len(x[i])))		
#     elif( len(x[i]) > max_l ):
#     	x[i] = x[i][0:max_l]
# x = np.asarray(x)

# for i in range(len(x_test)):
#     if( len(x_test[i]) < max_l ):
#         x_test[i] = np.append(x_test[i],np.zeros(max_l-len(x_test[i])))        
#     elif( len(x_test[i]) > max_l ):
#         x_test[i] = x_test[i][0:max_l]
# x_test = np.asarray(x_test)
# y_test = test_y

# topic_train = np.asarray(topic_text_id)
# topic_test = np.asarray(test_topic)
# author_train = np.asarray(author_text_id)
# author_test = np.asarray(test_author)


# shuffle_indices = np.random.permutation(np.arange(len(y)))
# x_shuffled = x[shuffle_indices]
# y_shuffled = y[shuffle_indices]
# topic_train_shuffled = topic_train[shuffle_indices]
# author_train_shuffled = author_train[shuffle_indices]

# # Split train/test set
# # TODO: This is very crude, should use cross-validation

# dev_sample_index = -1 * int(FLAGS.dev_sample_percentage * float(len(y)))
# x_train, x_dev = x_shuffled[:dev_sample_index], x_shuffled[dev_sample_index:]
# topic_train, topic_dev = topic_train_shuffled[:dev_sample_index], topic_train_shuffled[dev_sample_index:]
# author_train, author_dev = author_train_shuffled[:dev_sample_index], author_train_shuffled[dev_sample_index:]
# y_train, y_dev = y_shuffled[:dev_sample_index], y_shuffled[dev_sample_index:]
# print("Train/Dev split: {:d}/{:d}".format(len(y_train), len(y_dev)))
# x_train = np.asarray(x_train)
# x_dev = np.asarray(x_dev)
# author_train = np.asarray(author_train)
# author_dev = np.asarray(author_dev)
# topic_train = np.asarray(topic_train)
# topic_dev = np.asarray(topic_dev)
# y_train = np.asarray(y_train)
# y_dev = np.asarray(y_dev)
# word_idx_map["@"] = 0
# rev_dict = {v: k for k, v in word_idx_map.items()}

# # Training
# # ==================================================

# with tf.Graph().as_default():

#     sess = tf.Session(config=session_conf)
#     with sess.as_default():
#         cnn = TextCNN(
#             sequence_length=max_l,
#             num_classes=len(y_train[0]) ,
#             vocab_size=len(vocab),
#             word2vec_W = W,
#             word_idx_map = word_idx_map,
#             user_embeddings = user_embeddings,
#             topic_embeddings = topic_embeddings,
#             embedding_size=FLAGS.embedding_dim,
#             batch_size=FLAGS.batch_size,
#             filter_sizes=list(map(int, FLAGS.filter_sizes.split(","))),
#             num_filters=FLAGS.num_filters,
#             l2_reg_lambda=FLAGS.l2_reg_lambda)

#         # Define Training procedure
#         global_step = tf.Variable(0, name="global_step", trainable=False)
#         optimizer = tf.train.AdamOptimizer(1e-3)
#         grads_and_vars = optimizer.compute_gradients(cnn.loss)
#         train_op = optimizer.apply_gradients(grads_and_vars, global_step=global_step)
#         saver = tf.train.Saver(tf.global_variables(), max_to_keep=FLAGS.num_checkpoints)
#         writer = tf.summary.FileWriter('./graphs', sess.graph)
#         sess.run(tf.global_variables_initializer())


# def train_step(x_batch, author_batch, topic_batch, y_batch):
#     """
#     A single training step
#     """
#     feed_dict = {
#       cnn.input_x: x_batch,
#       cnn.input_author: author_batch,
#       cnn.input_topic: topic_batch,
#       cnn.input_y: y_batch,
#       cnn.dropout_keep_prob: FLAGS.dropout_keep_prob
#     }
#     _, step, loss, accuracy = sess.run(
#         [train_op, global_step, cnn.loss, cnn.accuracy],
#         feed_dict)
#     time_str = datetime.datetime.now().isoformat()
#     return loss, accuracy

# def dev_step(x_batch, author_batch, topic_batch, y_batch, writer=None):
#     """
#     Evaluates model on a dev set
#     """
#     feed_dict = {
#       cnn.input_x: x_batch,
#       cnn.input_author: author_batch,
#       cnn.input_topic: topic_batch,
#       cnn.input_y: y_batch,
#       cnn.dropout_keep_prob: 1.0
#     }
#     step, loss, conf_mat = sess.run(
#         [global_step, cnn.loss, cnn.confusion_matrix],
#         feed_dict)
#     return loss, conf_mat
    

# # Generate batches
# batches = data_helpers.batch_iter(
#     list(zip(x_train, author_train, topic_train, y_train)), FLAGS.batch_size, FLAGS.num_epochs)
# dev_batches = data_helpers.batch_iter(
#     list(zip(x_dev, author_dev, topic_dev, y_dev)), FLAGS.batch_size, FLAGS.num_epochs)
# # Training loop. For each batch...

# train_loss = []
# train_acc = []
# best_acc = 0
# for batch in batches:
#     x_batch, author_batch, topic_batch, y_batch = zip(*batch)
#     x_batch = np.asarray(x_batch)
#     author_batch = np.asarray(author_batch)
#     topic_batch = np.asarray(topic_batch)
#     y_batch = np.asarray(y_batch)
#     t_loss, t_acc = train_step(x_batch, author_batch, topic_batch, y_batch)
#     current_step = tf.train.global_step(sess, global_step)
#     train_loss.append(t_loss)
#     train_acc.append(t_acc)
#     if current_step % FLAGS.evaluate_every == 0:
#         print(current_step)
#         print("Train loss {:g}, Train acc {:g}".format(np.mean(np.asarray(train_loss)), np.mean(np.asarray(train_acc))))
#         train_loss = []
#         train_acc = []
#         # Divide into batches
#         dev_batches = data_helpers.batch_iter_dev(list(zip(x_dev, author_dev, topic_dev, y_dev)), FLAGS.batch_size)
#         dev_loss = []
#         ll = len(dev_batches)
#         conf_mat = np.zeros((2,2))
#         for dev_batch in dev_batches:
#             x_dev_batch = x_dev[dev_batch[0]:dev_batch[1]]
#             author_dev_batch = author_dev[dev_batch[0]:dev_batch[1]]
#             topic_dev_batch = topic_dev[dev_batch[0]:dev_batch[1]]
#             y_dev_batch = y_dev[dev_batch[0]:dev_batch[1]]
#             a, b = dev_step(x_dev_batch, author_dev_batch, topic_dev_batch, y_dev_batch)
#             dev_loss.append(a)
#             conf_mat += b
#         valid_accuracy = float(conf_mat[0][0]+conf_mat[1][1])/len(y_dev)
#         print("Valid loss {:g}, Valid acc {:g}".format(np.mean(np.asarray(dev_loss)), valid_accuracy))
#         print("Valid - Confusion Matrix: ")
#         print(conf_mat)
#         test_batches = data_helpers.batch_iter_dev(list(zip(x_test, author_test, topic_test, y_test)), FLAGS.batch_size)
#         test_loss = []
#         conf_mat = np.zeros((2,2))
#         for test_batch in test_batches:
#             x_test_batch = x_test[test_batch[0]:test_batch[1]]
#             author_test_batch = author_test[test_batch[0]:test_batch[1]]
#             topic_test_batch = topic_test[test_batch[0]:test_batch[1]]
#             y_test_batch = y_test[test_batch[0]:test_batch[1]]
#             a, b = dev_step(x_test_batch, author_test_batch, topic_test_batch, y_test_batch)
#             test_loss.append(a)
#             conf_mat += b
#         print("Test loss {:g}, Test acc {:g}".format(np.mean(np.asarray(test_loss)), float(conf_mat[0][0]+conf_mat[1][1])/len(y_test)))
#         print("Test - Confusion Matrix: ")
#         print(conf_mat)
#         sys.stdout.flush()
#         if best_acc < valid_accuracy:
#             best_acc = valid_accuracy
#             directory = "./models"
#             if not os.path.exists(directory):
#                 os.makedirs(directory)
#             saver.save(sess, directory+'/main_balanced_user_plus_topic', global_step=1)
