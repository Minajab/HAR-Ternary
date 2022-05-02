import os
import torch
import torch.nn as nn
from model import get_model_full, get_model_to_quantify
# from data import train_loader, test_loader
import data_preprocess
import test_and_val as test

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')


def load_data_fn(dataset_name, batch_size):
    train_loader, test_loader = data_preprocess.load(batch_size=batch_size, dataset=dataset_name)
    return train_loader, test_loader


def get_model(dataset_name, kernel_size=3, model_type='float'):
    if dataset_name == 'uci_har':
        num_features = 9
        num_classes = 6
        num_timesteps = 128
        name_prefix = 'uci_har'

    elif dataset_name == 'motion_sense':
        num_features = 12
        num_classes = 6
        num_timesteps = 50
        name_prefix = 'motion_sense'
    else:
        raise Exception("Sorry, dataset could not be found!")
    if 'ternary' in model_type:
        return get_model_to_quantify(n_timesteps=num_timesteps, n_classes=num_classes,
                                     name_prefix=name_prefix,
                                     num_features=num_features, kernel_size=kernel_size)
    else:
        return get_model_full(n_timesteps=num_timesteps, n_classes=num_classes, name_prefix=name_prefix,
                              num_features=num_features, kernel_size=kernel_size)


def train(idx=0):
    original_idx = idx
    best_results = {}
    batch_size = 256
    ### load data
    dataset_name = 'motion_sense'
    train_loader, test_loader = load_data_fn(dataset_name, batch_size)

    for kernel_size in [9, 11]:
        best_acc = 0
        idx = original_idx
        for idx in range(idx, idx + 2):
            ### param
            num_epochs = 50
            max_acc = 0.0
            decay_idx = 0
            # kernel_size = 7
            criterion = nn.CrossEntropyLoss()
            total_step = len(train_loader)
            ## get model
            model = get_model(dataset_name, kernel_size=kernel_size)
            ########
            pytorch_total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print("total_params: ", pytorch_total_params)

            postfix = f'{dataset_name}_kernel_{kernel_size}_all_epoch300_{idx}'
            matrices_file_name = f"logs/float_model_log_{postfix}.txt"
            matrices_acc_file_name = f"logs/float_model_acc_{postfix}.txt"

            # for lr in [1e-5, 1e-6, 1e-7]:5e-4, 1e-4,
            # for lr in [.0001, .0001, .00005, .00002, .00001, .000005,  .000003, .000002, .000001, .0000002, .0000001]:# .00001]: # [0.001, 0.0001, 0.00001, 0.000001 ]:
            # for lr in [.0001,.0001, .00005, .00002, .00001, .000005,  .000003, .000002, .000001, .0000002, .0000001]:# .00001]: # [0.001, 0.0001, 0.00001, 0.000001 ]:

            # lr_list = [3e-4,1e-5, 1e-5, 5e-6, 1e-6, 5e-7, 1e-7]
            lr_list = [1e-4, 1e-5, 1e-5, 1e-6, 1e-6, 1e-7, 1e-7]
            print(lr_list)
            for lr in lr_list:
                decay_idx += 1
                optimizer = torch.optim.Adam(model.parameters(), lr=lr)

                for epoch in range(num_epochs):
                    for i, (images, labels) in enumerate(train_loader):
                        images = images.to(device)
                        labels = labels.to(device)
                        labels = torch.max(labels, 1)[1]
                        # Forward pass
                        model = model.float()
                        outputs = model(images.float())
                        loss = criterion(outputs, labels)

                        # Backward and optimize
                        optimizer.zero_grad()
                        loss.backward()
                        optimizer.step()

                        if (i + 1) % total_step == 0 and epoch % 2 == 0:
                            train_loss = test.validation_loss(model, train_loader, criterion)
                            val_loss = test.validation_loss(model, test_loader, criterion)
                            epoch_idx = num_epochs * (decay_idx - 1) + epoch

                            # if val_loss.item() < max_val:
                            with open(matrices_file_name, "a") as metrics_handle:
                                string = f'Epoch [{epoch_idx + 1}/{num_epochs}], Step [{i + 1}/{total_step}], ' \
                                         f'lr: {lr:.5f}, Loss: {train_loss.item():.6f}, Val_Loss: {val_loss.item():.6f}\n'
                                metrics_handle.write(string)

                            print(string)
                            # max_val = val_loss.item()
                            max_acc = test.validation_acc(model, train_loader, test_loader, max_acc, epoch_idx,
                                                          matrices_acc_file_name, model_name=f'{postfix}_float')
                            #
                            # max_acc = test.validation_acc(model, train_loader, test_loader, max_acc, matrices_acc_file_name)
                            if best_acc <= max_acc:
                                best_acc = max_acc
                                best_results[kernel_size] = idx
                test.save_model(model, model_name=f'{postfix}_float')
    for kernel_size in [9, 11]:
        print("Best Result Dataset Name {0} Kernel {1} IDX {2}".format(dataset_name, kernel_size,
                                                                       best_results[kernel_size]))


if __name__ == '__main__':
    torch.set_default_tensor_type('torch.DoubleTensor')
    train()
    # save_model()
    # test()
