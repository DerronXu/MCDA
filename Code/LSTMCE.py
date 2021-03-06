#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   # see issue #152
os.environ["CUDA_VISIBLE_DEVICES"]="3"
import tensorflow as tf


from LoadData import LoadData as loadData
import numpy as np

def get_dimension(file):
    with open(file, 'r') as f:
        first_line = f.readline()
        words = first_line.split(",")
        return len(words)

def merge_list(list1, list2):
    return list1 + list2

def RNN(X, weights, biases, n_steps, n_hidden_units, batch_size, n_dim, num_stacked_layers, in_keep_prob, out_keep_prob):
    # X ==> (128 batches * 28 steps, 28 inputs)
    X = tf.reshape(X, [-1, n_dim])

    # X_in = W*X + b
    X_in = tf.matmul(X, weights['in']) + biases['in']
    # X_in ==> (128 batches, 28 steps, 128 hidden)
    X_in = tf.reshape(X_in, [-1, n_steps, n_hidden_units])
    #


    cells = []
    for i in range(num_stacked_layers):
        with tf.variable_scope('RNN_{}'.format(i)):
            cell = tf.contrib.rnn.LSTMCell(n_hidden_units, use_peepholes=True)
            cell_dropout = tf.contrib.rnn.DropoutWrapper(cell, input_keep_prob=in_keep_prob,
                                                         output_keep_prob=out_keep_prob)
            cells.append(cell_dropout)
    lstm_cell = tf.contrib.rnn.MultiRNNCell(cells)


    #lstm_cell = tf.contrib.rnn.BasicLSTMCell(n_hidden_units, forget_bias=1.0, state_is_tuple=True)
    init_state = lstm_cell.zero_state(batch_size, dtype=tf.float64) #

    outputs, final_state = tf.nn.dynamic_rnn(lstm_cell, X_in, initial_state=init_state, time_major=False)
    feature = []
    feature = final_state[num_stacked_layers - 1][1]
    results = tf.matmul(feature, weights['out']) + biases['out']
    return results

if __name__ == '__main__':

    filename = 'xxxxxx'

    num_of_sample = len(["" for line in open(filename, "r")])

    n_dim = get_dimension(filename) - 1

    data = loadData(filename, num_of_sample)


    n_hidden_units = 50
    n_classes = 2
    batch_size = 200
    n_steps = 200
    lr = 0.001  # learning rate
    training_iters = 300  # train step
    stepwidth = 100

    # num of stacked lstm layers
    num_stacked_layers = 2

    in_keep_prob = 0.5
    out_keep_prob = 1
    lambda_l2_reg = 0.001

    tf.reset_default_graph()

    # 对 weights biases 初始值的定义
    # weights = {
    #     # shape (28, 128)
    #     'in': tf.Variable(tf.random_normal([n_dim, n_hidden_units], dtype=tf.float64)),
    #     # shape (128, 10)
    #     'out': tf.Variable(tf.random_normal([n_hidden_units, n_classes], dtype=tf.float64))
    # }
    # biases = {
    #     # shape (128, )
    #     'in': tf.Variable(tf.constant(0.1, shape=[n_hidden_units, ], dtype=tf.float64)),
    #     # shape (10, )
    #     'out': tf.Variable(tf.constant(0.1, shape=[n_classes, ], dtype=tf.float64))
    # }

    weights = {
        'in': tf.get_variable('Weights_in', \
                              shape=[n_dim, n_hidden_units], \
                              dtype=tf.float64, \
                              initializer=tf.truncated_normal_initializer()),
        'out': tf.get_variable('Weights_out', \
                               shape=[n_hidden_units, n_classes], \
                               dtype=tf.float64, \
                               initializer=tf.truncated_normal_initializer()),
    }
    biases = {
        'in': tf.get_variable('Biases_in', \
                              shape=[n_hidden_units,], \
                              dtype=tf.float64, \
                              initializer=tf.constant_initializer(0.)),
        'out': tf.get_variable('Biases_out', \
                               shape=[n_classes, ], \
                               dtype=tf.float64, \
                               initializer=tf.constant_initializer(0.)),
    }

    # x y placeholder
    x = tf.placeholder(tf.float64, [None, n_steps, n_dim])
    y = tf.placeholder(tf.float64, [None, n_classes])

    pred = RNN(x, weights, biases, n_steps, n_hidden_units, batch_size, n_dim, num_stacked_layers, in_keep_prob, out_keep_prob)
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))

    # L2 regularization for weights and biases
    reg_loss = 0
    for tf_var in tf.trainable_variables():
        if 'Biases_' in tf_var.name or 'Weights_' in tf_var.name:
            reg_loss += lambda_l2_reg * tf.reduce_mean(tf.nn.l2_loss(tf_var))
    cost += reg_loss


    train_op = tf.train.AdamOptimizer(lr).minimize(cost)

    correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float64))

    # init= tf.initialize_all_variables() # tf 马上就要废弃这种写法
    # 替换成下面的写法:
    init = tf.global_variables_initializer()

    start = 1
    end = 100000
    case_id = [372589, 160302]
    label_v = [1.0, 0.0]
    tr_data, tr_y = data.generateList(n_steps, stepwidth, start, end, label_v)
    # generateBatch(n_steps, batch_size, stepwidth, start, end, label_v)

    label_v = [0.0, 1.0]
    listNum = len(tr_data)
    tr_data_case, tr_y_case = data.generateRepeatList((int)(listNum/2), case_id[0] - n_steps, case_id[0], label_v)
    batch_xs = merge_list(tr_data, tr_data_case)
    batch_ys = merge_list(tr_y, tr_y_case)

    tr_data_case, tr_y_case = data.generateRepeatList((int)(listNum / 2), case_id[1] - n_steps, case_id[1], label_v)

    batch_xs = merge_list(batch_xs, tr_data_case)
    batch_ys = merge_list(batch_ys, tr_y_case)




    testing = data.generateTest(n_steps, batch_size, stepwidth)


    with tf.Session() as sess:
        sess.run(init)
        epoch = 0
        while epoch < training_iters:
            training_accuracy = 0
            batch_num = int(len(batch_xs)/batch_size)
            idx = np.random.permutation(len(batch_xs))
            xx = np.array(batch_xs)[idx]
            yy = np.array(batch_ys)[idx]

            for i in range(0, batch_num):
                bt = xx[i*batch_size:(i+1)*batch_size]
                by = yy[i*batch_size:(i+1)*batch_size]
                sess.run([train_op], feed_dict={x: bt, y: by})
                ac = accuracy.eval(feed_dict={x: bt, y: by})
                training_accuracy += ac
            training_accuracy /= batch_num

            if epoch % 2 == 0:
                print(training_accuracy)
            epoch += 1
        predict=[]

        p_label = tf.argmax(pred, 1)
        for bt in testing:
            pred_label = p_label.eval(feed_dict={x: bt})
            predict= np.concatenate((predict, pred_label), axis=0)

        print(predict.tolist())