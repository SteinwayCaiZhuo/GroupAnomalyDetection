import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os, argparse


def get_attack_interval(label):
    starts = []
    ends = []

    for i in range(len(label) - 1):
        if (label[i] == 0 and label[i + 1] == 1):
            starts.append(i + 1)
        if (label[i] == 1 and label[i + 1] == 0):
            ends.append(i + 1)
    int_num = np.min((len(starts), len(ends)))
    return np.concatenate((starts[:int_num], ends[:int_num])).reshape(2, int_num).transpose(1, 0)


def eval_measure(test, pred, test_th=0.02, pred_th=0.24):
    TP, FP, TN, FN = 0, 0, 0, 0
    for i in range(len(test)):
        if (test[i] > test_th):
            if (pred[i] > pred_th):
                TP += 1
            elif (pred[i] <= pred_th):
                FN += 1
        elif (test[i] <= test_th):
            if (pred[i] > pred_th):
                FP += 1
            elif (pred[i] <= pred_th):
                TN += 1
    if (TP + FP == 0):
        print("TP+FP==0")
        return (0, 0, 0)
    if (TP + FN == 0):
        print("TP+FN==0")
        return (0, 0, 0)

    pre = TP / (TP + FP)
    rec = TP / (TP + FN)
    F1 = 2 * pre * rec / (pre + rec) if (pre + rec) > 0 else 0
    # print("pre: ", pre, ";  rec: ", rec, "; F1: ", F1)
    return (pre, rec, F1)


if (__name__ == "__main__"):

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='wadi',
                        choices=['wadi', 'swat'])
    parser.add_argument('--dataset_path', type=str, default='../../data')
    parser.add_argument('--dataset_filename', type=str, default='_1.npy')
    parser.add_argument('--mdi_method', type=str, default='gaussian')
    parser.add_argument('--use_bnaf', type=int, default=1,
                        choices=[1, 0])
    parser.add_argument('--output_score', type=str, default="a")
    args = parser.parse_args()
    args.use_bnaf = bool(args.use_bnaf)

    data_attack = np.load('../../data/wadi/attack_level.npy')

    anomaly_intervals_gth = get_attack_interval(data_attack)
    print("anomaly_intervals = ", anomaly_intervals_gth)

    anomaly_level = np.zeros(data_attack.shape[0])
    for i in range(len(anomaly_intervals_gth)):
        for j in range(anomaly_intervals_gth[i][0], anomaly_intervals_gth[i][1]):
            anomaly_level[j] = 1
    region_proposals = np.load("region_proposals_{}_{}_{}.npy".format(
        args.dataset, 'bnaf' if args.use_bnaf else 'nonbnaf', args.mdi_method))
    region_proposals_max = np.argmax(region_proposals[:, -1])
    print("max score interval:", region_proposals[region_proposals_max])

    region_proposals_df = pd.DataFrame({"start": region_proposals[:, 0], \
                                        "end": region_proposals[:, 1], \
                                        "score": region_proposals[:, 2]})
    print(region_proposals_df.head())
    region_proposals_df = region_proposals_df.sort_values("score", ascending=False)
    print(region_proposals_df.head())
    anomaly_scores = np.zeros(len(region_proposals))

    anomaly_time_scores = np.zeros(data_attack.shape[0])
    anomaly_time_weights = np.zeros(data_attack.shape[0]) + 1e-7

    for i in range(len(region_proposals)):
        start, end, score = int(region_proposals[i][0]), int(region_proposals[i][1]), region_proposals[i][2]
        if np.isnan(score):
            print("i=",i, "score = ",score)
        anomaly_time_scores[start:end] += score/np.power(end-start, -0.2)
        anomaly_time_weights[start:end] += 1/np.power(end-start, -0.2)

    anomaly_time_scores_aver = anomaly_time_scores / anomaly_time_weights
    print("np.corrcoeff time score:", np.corrcoef(anomaly_time_scores_aver, anomaly_level))
    np.save(args.output_score+".npy", anomaly_time_scores_aver)

    max_f1 = 0
    for pred_th in np.linspace(np.quantile(anomaly_time_scores_aver, 0.8), np.quantile(anomaly_time_scores_aver, 0.99),
                               200):
        res = eval_measure(anomaly_level, anomaly_time_scores_aver, test_th=0.5, pred_th=pred_th)

        if res[2] > max_f1:
            max_f1 = res[2]
        print("for pred_th = ", pred_th, "res = ", res)
    print("max f1: ", max_f1)

    plt.figure(figsize=(20, 10))

    range2 = np.arange(0, data_attack.shape[0])
    plt.plot(range2, anomaly_time_scores_aver[range2], color="b")
    for j in range(len(anomaly_intervals_gth)):
        plt.axvspan(anomaly_intervals_gth[j][0], anomaly_intervals_gth[j][1], alpha=0.3, color="red")
    plt.title('{}_{}_{}.score'.format(args.dataset, 'bnaf' if args.use_bnaf else 'nonbnaf', args.mdi_method))
    plt.show()
