import torch
import torch.nn.functional as F
from torch_geometric.nn import GMMConv
from gnn_model import GnnModel

import numpy as np
import os

import scipy.stats
import matplotlib.pyplot as plt


class MinimalGmmConvModel(GnnModel):
    def __init__(self,
                 config,
                 train_writer,
                 val_writer,
                 epoch=0,
                 train_batch_iteration=0,
                 val_batch_iteration=0,
                 model_type=None):

        super(MinimalGmmConvModel, self).__init__(
            config=config,
            train_writer=train_writer,
            val_writer=val_writer,
            epoch=epoch,
            train_batch_iteration=train_batch_iteration,
            val_batch_iteration=val_batch_iteration,
            model_type=model_type)

    def layers(self):
        # self.conv_in = GMMConv(
        #     in_channels=self.config.feature_dimensionality,
        #     out_channels=self.model_type.out_channels,
        #     dim=self.config.pseudo_dimensionality,
        #     kernel_size=self.config.kernel_size,
        #     bias=self.config.use_bias)

        self.conv_in = GMMConv(
           in_channels=self.config.feature_dimensionality,
           out_channels=self.config.hidden_units,
           dim=self.config.pseudo_dimensionality,
           kernel_size=self.config.kernel_size,
           bias=self.config.use_bias)

        self.fc = torch.nn.Linear(in_features=self.config.hidden_units, out_features=self.model_type.out_channels, bias=self.config.use_bias)

    def forward(self, data):
        x, edge_index, edge_attr = data.x, data.edge_index, data.edge_attr

        if self.training:
            self.write_to_variable_summary(self.conv_in.mu, 'in_layer', 'weights_mu')
            self.write_to_variable_summary(self.conv_in.sigma, 'in_layer', 'weights_sigma')
            self.write_to_variable_summary(self.conv_in.lin.weight, 'in_layer', 'weights_matmul')
            if self.config.use_bias:
                self.write_to_variable_summary(self.conv_in.lin.bias, 'in_layer', 'weights_matmul_bias')

        x = self.conv_in(x=x, edge_index=edge_index, pseudo=edge_attr)
        # self.write_to_variable_summary(x, 'in_layer', 'pre_activations')

        # x = getattr(F, self.config.dropout_type)(x, p=self.config.dropout_prob, training=self.training)

        # x = getattr(torch, self.config.non_linearity)(x)
        self.write_to_variable_summary(x, 'in_layer', 'outputs')

        if self.training:
            self.write_to_variable_summary(self.fc.weight, 'fc_layer', 'weights')
            if self.config.use_bias:
                self.write_to_variable_summary(self.fc.bias, 'fc_layer', 'bias')

        x = self.fc(x)
        self.write_to_variable_summary(x, 'fc_layer', 'pre_activations')
        x = self.model_type.out_nonlinearity(x)
        self.write_to_variable_summary(x, 'fc_layer', 'outputs')

        return x

    def plot_gaussian_kernels(self):

        if self.config.pseudo_dimensionality > 1:
            print('Cannot plot gaussian kernels because pseudo dimensionality > 1')
            return

        print('Plotting the gaussian kernels ...')
        K = self.config.kernel_size

        # one picture per input channel
        for i in range(self.conv_in.in_channels):

            for j in range(K):
                mu = self.conv_in.mu[i*K+j].detach().numpy()
                sigma = self.conv_in.sigma[i*K+j].detach().numpy()

                x = np.linspace(mu - 3*sigma, mu + 3*sigma, 100)
                y = MinimalGmmConvModel.gaussian_kernel(x, mu, sigma)
                # plt.plot(x, scipy.stats.norm.pdf(x, mu, sigma))
                plt.plot(x,y)

            plt.savefig(os.path.join(self.config.temp_dir, 'layer0_kernel{}'.format(i)))

    def gaussian_kernel(x, mu, sigma):
        gaussian = -0.5 * (x - mu) ** 2
        gaussian = gaussian / (1e-14 + sigma ** 2)
        gaussian = np.exp(gaussian)
        return gaussian
