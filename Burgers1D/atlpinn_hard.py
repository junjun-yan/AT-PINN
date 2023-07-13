import sys

sys.path.append("/root/ATLPINN")

import torch
from utilities import relative_error
from atlpinns import ATLPINN_Burgers1D
from networks import NeuralNetwork_Hard
from dataset import Dataset1D
import numpy as np
import time

torch.manual_seed(1234)
np.random.seed(1234)

device = torch.device(f"cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Use GPU: {torch.cuda.is_available()}\n")

### hypoparameters
init_weight = 80
bound_weight = 70
learning_rate = 0.001
shared_layers = [2] + 5 * [50]
special_layers = 2 * [50] + [1]

nu = 0.01
N_init = 100
N_bound = 100
N_test = 20000
N_eqns = 10000
task_number = 2
batch_size = 20000

data_path = r'/root/autodl-tmp/133136'
print_path = r'/root/ATLPINN/log4loss/burgers_hard_+1_new.txt'


def run(tasks):
    create_date = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    log_path = "/root/tf-logs/burgers-hard-%d-%s" % (tasks[0], create_date)

    ### get data
    dataset = Dataset1D(data_path, tasks)
    X_init, Y_init = dataset.get_init_points(N_init)
    X_l_bound, X_r_bound = dataset.get_bound_points(N_bound)
    X_test, Y_test = dataset.get_test_points(N_test)
    X_eqns, _ = dataset.get_sample_points(N_eqns)
    X, Y = dataset.get_all_points()

    ### modal and train | test
    network = NeuralNetwork_Hard(X, shared_layers, special_layers, task_number, device)
    model = MTPINN_Burgers1D(X_init, Y_init, X_l_bound, X_r_bound, X_test, Y_test, X_eqns, network, batch_size, nu,
                             init_weight, bound_weight, log_path, learning_rate, task_number, device)

    model.logging("number init: %d" % X_init.shape[0])
    model.logging("number bound: %d" % X_l_bound.shape[0])
    model.logging("number sample: %d" % X_eqns.shape[0])
    model.logging("number test: %d" % X_test.shape[0])

    # train
    model.train(adam_it=20000, lbfgs_it=0, clip_grad=False, decay_it=10000, decay_rate=0.5, print_it=10,
                evaluate_it=100, cosine_sim=False)

    # test
    Y_pred = model.predict(X.to(device))
    for task in range(task_number):
        error = relative_error(Y_pred[task], Y[task].to(device))

        # save result
        model.logging(f'task {tasks[task]}, l2 related error: {error:.3e}')
        with open(print_path, 'a+') as f:
            f.write(f'task {tasks[task]}, l2 related error: {error:.3e}\n')

        # save prediction
        hard_path = "/root/ATLPINN/output/burgers_hard_%d.npy" % (tasks[task])
        hard_data = {'u': Y_pred[task]}
        np.save(hard_path, hard_data)


if __name__ == '__main__':
    with open('/root/ATLPINN/Burgers1D/index.txt', 'r') as f:
        all_tasks = f.readlines()

        for i in range(0, 100, 2):
            task1 = int(all_tasks[i].strip())
            task2 = int(all_tasks[i + 1].strip())
            tasks = [task1, task2]
            run(tasks)