
import matplotlib.pyplot as plt

import os
os.environ["CUDA_DEVICE_ORDER" ] ="PCI_BUS_ID"   # see issue #152
os.environ["CUDA_VISIBLE_DEVICES" ] ="2"
import tensorflow as tf



from LoadData import LoadData as loadData
from TripletGenerator import TripletGenerator as batchPool

import numpy as np

def get_dimension(file):
    with open(file, 'r') as f:
        first_line = f.readline()
        words = first_line.split(",")
        return len(words)

def merge_list(list1, list2):
    return list1 + list2

def RNN(X1, X2, X3, weights, biases, instance_length, instance_step_width, n_hidden_units, batch_size, n_dim, num_stacked_layers, in_keep_prob, out_keep_prob, w, V, U):
    #lstm_cell = tf.contrib.rnn.BasicLSTMCell(n_hidden_units, forget_bias=1.0, state_is_tuple=True)
    cells = []
    for i in range(num_stacked_layers):
        with tf.variable_scope('RNN_{}'.format(i)):
            cell = tf.contrib.rnn.LSTMCell(n_hidden_units, use_peepholes=True)
            cell_dropout = tf.contrib.rnn.DropoutWrapper(cell, input_keep_prob=in_keep_prob,
                                                         output_keep_prob=out_keep_prob)
            cells.append(cell_dropout)
    lstm_cell = tf.contrib.rnn.MultiRNNCell(cells)


    feature1 = mi_lstm(lstm_cell, X1, instance_length, instance_step_width, n_hidden_units, n_dim, num_stacked_layers, w, V, U)

    feature2 = mi_lstm(lstm_cell, X2, instance_length, instance_step_width, n_hidden_units, n_dim, num_stacked_layers, w, V, U)

    feature3 = mi_lstm(lstm_cell, X3, instance_length, instance_step_width, n_hidden_units, n_dim, num_stacked_layers, w, V, U)


    return feature1, feature2, feature3

def attention(w, V, U, h_list_tensor, length, K):
    z_bt = []
    #A = tf.transpose(tf.matmul(tf.transpose(w), tf.tanh(tf.matmul(V, tf.transpose(h_list_tensor)))))

    A= tf.transpose(tf.nn.softmax(tf.matmul(tf.transpose(w), tf.multiply(tf.tanh(tf.matmul(V, tf.transpose(h_list_tensor))), \
                         tf.sigmoid(tf.matmul(U, tf.transpose(h_list_tensor)))))))

    for i in range(0, length):
        h_block = h_list_tensor[i * K:(i + 1) * K]
        ##### max, mean, attention1, attention2

        #z = tf.reduce_max(h_block, axis=0)
        #z = tf.reduce_mean(h_block, axis=0)

        oneblock = A[i * K:(i + 1) * K]

        a = tf.nn.softmax(oneblock)


        z = tf.reduce_sum(tf.matmul(tf.transpose(a), h_block), 0)

        z_bt.append(z)
    return tf.convert_to_tensor(z_bt, dtype=tf.float64)
def mi_lstm(lstm_cell, X, instance_length, stepwidth, n_hidden_units, n_dim, num_stacked_layers, w, V, U):
    length = X.get_shape()[0]

    x_list = tf.split(X, length, 0)

    ins_list = []

    for i in range(0, length):
        data = tf.squeeze(x_list[i])
        data_length = data.get_shape()[0]
        K = 0
        for j in range(0, data_length - instance_length + 1, stepwidth):
            instance = data[j:j + instance_length]
            ins_list.append(instance)
            K += 1

    bt_ins = tf.convert_to_tensor(ins_list)
    init_state = lstm_cell.zero_state(len(ins_list), dtype=tf.float64)

    h_list_tensor = LSTM(bt_ins, weights, biases, lstm_cell, init_state, n_dim, instance_length, n_hidden_units, num_stacked_layers)

    res = attention(w, V, U, h_list_tensor, length, K)
    return res

def LSTM(X, weights, biases, cell, init_state, n_dim, n_steps, n_hidden_units, num_stacked_layers):
    # X ==> (128 batches * 28 steps, 28 inputs)
    X = tf.reshape(X, [-1, n_dim])

    # X_in = W*X + b
    X_in = tf.matmul(X, weights['in']) + biases['in']
    # X_in ==> (128 batches, 28 steps, 128 hidden)
    X_in = tf.reshape(X_in, [-1, n_steps, n_hidden_units])
    #
    outputs, final_state = tf.nn.dynamic_rnn(cell, X_in, initial_state=init_state, time_major=False)

    feature = final_state[num_stacked_layers - 1][1]

    return feature



def distance(z1, z2):
    ## l2diff
    #return tf.sqrt(tf.reduce_sum(tf.square(tf.subtract(z1, z2)), reduction_indices=1))
    return tf.sqrt(tf.reduce_sum(tf.square(z1 - z2), 1))

if __name__ == '__main__':
 
    filename = 'xxxxxx'

    num_of_sample = len(["" for line in open(filename, "r")])

    n_dim = get_dimension(filename) - 1

    data = loadData(filename, num_of_sample)

    n_hidden_units = 50
    n_classes = 2
    batch_size = 400
    n_steps = 200
    lr = 0.001  # learning rate
    training_iters = 700  # train step
    stepwidth = 100
    margin = 50

    # num of stacked lstm layers
    num_stacked_layers = 1

    instance_length = 50
    instance_step_width = 10
    L = 20

    in_keep_prob = 0.5
    out_keep_prob = 1
    lambda_l2_reg = 0.001

    tf.reset_default_graph()

    # weights = {
    #     # shape (28, 128)
    #     'in': tf.Variable(tf.random_normal([n_dim, n_hidden_units], dtype=tf.float64)),
    # }
    # biases = {
    #     # shape (128, )
    #     'in': tf.Variable(tf.constant(0.1, shape=[n_hidden_units, ], dtype=tf.float64)),
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
                              shape=[n_hidden_units, ], \
                              dtype=tf.float64, \
                              initializer=tf.constant_initializer(0.)),
        'out': tf.get_variable('Biases_out', \
                               shape=[n_classes, ], \
                               dtype=tf.float64, \
                               initializer=tf.constant_initializer(0.)),
    }

    M = n_hidden_units
    w = tf.Variable(tf.constant(0.1, shape=[L, 1], dtype=tf.float64))
    V = tf.Variable(tf.constant(0.1, shape=[L, M], dtype=tf.float64))
    U = tf.Variable(tf.constant(0.1, shape=[L, M], dtype=tf.float64))

    # x placeholder
    x1 = tf.placeholder(tf.float64, [batch_size, n_steps, n_dim])
    x2 = tf.placeholder(tf.float64, [batch_size, n_steps, n_dim])
    x3 = tf.placeholder(tf.float64, [batch_size, n_steps, n_dim])

    anchor_output, positive_output, negative_output = RNN(x1, x2, x3, weights, biases, \
                                                          instance_length, instance_step_width, n_hidden_units, \
                                                          batch_size, n_dim, num_stacked_layers, in_keep_prob, \
                                                          out_keep_prob, w, V, U)
    d_pos = tf.reduce_sum(tf.square(anchor_output - positive_output), 1)
    d_neg = tf.reduce_sum(tf.square(anchor_output - negative_output), 1)

    loss = tf.maximum(tf.cast(0., tf.float64), margin + d_pos - d_neg)
    cost = tf.reduce_mean(loss)

    # L2 regularization for weights and biases
    reg_loss = 0
    for tf_var in tf.trainable_variables():
        if 'Biases_' in tf_var.name or 'Weights_' in tf_var.name:
            reg_loss += lambda_l2_reg * tf.reduce_mean(tf.nn.l2_loss(tf_var))
    cost += reg_loss

    train_op = tf.train.AdamOptimizer(lr).minimize(cost)

    # optimizer = tf.train.AdamOptimizer(learning_rate=lr)
    # gvs = optimizer.compute_gradients(cost)
    # capped_gvs = [(tf.clip_by_value(grad, -1., 1.), var) for grad, var in gvs]
    # train_op = optimizer.apply_gradients(capped_gvs)

    init = tf.global_variables_initializer()

    start = 1
    end = 100000
    case_id = [372589, 160302]  # 513081
    label_v = [1.0, 0.0]
    negative, tr_y = data.generateList(n_steps, stepwidth, start, end, label_v)
    listNum = len(negative)

    label_v = [0.0, 1.0]
    anchor, tr_y_case1 = data.generateRepeatList(listNum, case_id[0] - n_steps, case_id[0], label_v)

    aps_cap_flag = False
    batch_data_pool = batchPool(aps_cap_flag)
    label_v = [0.0, 1.0]
    positive, tr_y_case2 = data.generateRepeatList(listNum, case_id[1] - n_steps, case_id[1], label_v)



    batch_data_pool.addTriplet(anchor, positive, negative)



    testing = data.generateTest(n_steps, batch_size, stepwidth)



    with tf.Session() as sess:
        sess.run(init)
        epoch = 0
        while epoch < training_iters:
            training_loss = 0
            stepNum = (int)(batch_data_pool.getTrainNum()/batch_size)
            step = 0
           # batch_data_pool.reshuffle()
            while step < stepNum:
                bt1, bt2, bt3 = batch_data_pool.next_batch(batch_size)

                sess.run([train_op], feed_dict={x1: bt1, x2: bt2, x3: bt3})
                loss = cost.eval(feed_dict={x1: bt1, x2: bt2, x3: bt3})
                training_loss += loss
                step += 1

            training_loss_avg = training_loss / ((step + 1) * batch_size)
            print(training_loss_avg)
            epoch += 1
        predict = []

        test_case = anchor[0: batch_size]

        dist_z1_z2_test = distance(anchor_output, positive_output)
        for bt in testing:
            dist_test = dist_z1_z2_test.eval(feed_dict={x1: bt, x2: test_case, x3: test_case})
            predict = np.concatenate((predict, dist_test), axis=0)

        print(predict.tolist())