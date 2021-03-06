import os
import sys
from typing import List
import numpy as np
import pandas as pd
import mykmeanssp

MSG_ERR_INVALID_INPUT = "Invalid Input!"
MSG_ERR_GENERIC = "An Error Has Occurred"

INFINITY = float('inf')
MAX_ITER_UNSPEC = 300


def main():
    np.random.seed(0)
    fit_params = extract_fit_params()
    results = KmeansAlgorithm(*fit_params)
    print('\n'.join([','.join(["%.4f"%y for y in x]) for x in results]))


def KmeansAlgorithm(*fit_params) -> List[List[float]]:
    return mykmeanssp.fit(*fit_params)


def extract_fit_params(should_print=True):
    k, max_iter, eps, datapoints_list = get_data_from_cmd()
    initial_centroids_list = KMeansPlusPlus(k, datapoints_list)
    initial_centroids_indices_as_written = [int(initial_centroids_list[i][0]) for i in range(len(initial_centroids_list))]
    if should_print: print(','.join([str(x) for x in initial_centroids_indices_as_written]))
    initial_centroids_indices_actual = select_actual_centroids(datapoints_list, initial_centroids_list)
    datapoints_list = [list(x) for x in list(datapoints_list[:,1:])] # remove index, convert to List[List[float]] for C
    dims_count = len(datapoints_list[0])
    point_count = len(datapoints_list)
    return (
        initial_centroids_indices_actual,
        datapoints_list,
        dims_count,
        k,
        point_count,
        max_iter,
        eps
    )


def KMeansPlusPlus(k: int, x: np.array) -> List[int]:
    np.random.seed(0)
    x = np.array(x)
    N, d = x.shape
    u = [None for _ in range(k)]
    u_idx = [-1 for _ in range(N)]
    P = [0 for _ in range(N)]
    D = [float('inf') for _ in range(N)]

    i = 0
    selection = np.random.choice(x[:,0])
    u[0] = x[np.where(x[:,0]==selection)]

    while (i+1) < k:
        for l in range(N):
            x_l = x[l] # remove index
            min_square_dist = float('inf')
            for j in range(0,i+1):
                u_j = u[j][0,:] # u.shape = (1,u.shape[0]) -> (u.shape[0],)
                square_dist = np.sum((x_l[1:] - u_j[1:])**2) # first item is an index
                min_square_dist = min(square_dist, min_square_dist)
            D[l] = min_square_dist
        D_sum = sum(D)
        P = D/D_sum

        i += 1
        selection = np.random.choice(x[:,0], p=P)
        u[i] = x[np.where(x[:,0]==selection)]
        continue

    centroids_without_padding = [a[0] for a in u]
    return centroids_without_padding


def KMeansPlusPlus_original(k: int, data: np.array) -> List[int]:
    # below is the original code I wrote for this
    # much more elegant but doesn't seem to reproduce the same result as the example...
    # calling np.random.choice(N, p=np.ones(N)/N) for the first time yields 54 instead of 44
    # so the randomization is obviously different
    # I think it makes no sense to force us to use the same randomization method as you
    data = np.copy(data)
    N, dims = data.shape

    D = np.ones(N)*np.inf
    P = np.ones(N)/N
    centroids_list = np.ones((k, dims)) * np.inf
    centroids_choice = np.ones(k, dtype=np.uint64) * (-1)

    np.random.seed(0)

    for i in range(1,k):
        centroids_choice[i] = np.random.choice(N, p=P)
        centroids_list[i] = data[int(centroids_choice[i])]
        for l in range(N):
            D[l] = np.min(np.sum(np.square(data[l]-centroids_list), axis=1))
        P = D/np.sum(D)
    return centroids_choice


def select_actual_centroids(data: List[List[float]], initial_centroids_list: List[List[float]]) -> List[int]:
    # incase we have duplicates, etc...
    initial_centroids_indices_actual = [None for centroid in initial_centroids_list]
    for i, centroid in enumerate(initial_centroids_list):
        loc = np.where(np.all(data==centroid,axis=1))[0] #[0] because this returns a tuple
        if len(loc) == 0: # or len(loc)>=2?
            exit_error()
        initial_centroids_indices_actual[i] = loc[0]
    return initial_centroids_indices_actual


def get_data_from_cmd():

    def _get_cmd_args():
        args = sys.argv
        if args[0] in ["python", "python3", "python.exe", "python3.exe"]:
            args = args[1:]
        if args[0][-3:] == ".py":
            args = args[1:]
        try:
            if len(args) == 4:  # without max_itr
                return int(args[0]), MAX_ITER_UNSPEC, float(args[1]), args[2], args[3]
            elif len(args) == 5:
                return int(args[0]), int(args[1]), float(args[2]), args[3], args[4]
            else:
                raise Exception()
        except:
            exit_invalid_input()

    def _validate_input_filenames(file_name1: str, file_name2: str) -> bool:
        for file in [file_name1, file_name2]:
            if not os.path.exists(file):
                exit_invalid_input()
            if not (file.lower().endswith("csv") or file.lower().endswith("txt")):
                exit_invalid_input()
        return True
    
    def _read_data_as_np(file_name1: str, file_name2: str) -> np.array:
        path_file1 = os.path.join(os.getcwd(), file_name1)
        path_file2 = os.path.join(os.getcwd(), file_name2)
        data_frame_1 = pd.read_csv(path_file1, header=None).rename({0: "index"}, axis=1)
        data_frame_2 = pd.read_csv(path_file2, header=None).rename({0: "index"}, axis=1)
        joined_data_frame = data_frame_1.join(
                                            data_frame_2.set_index('index'),
                                            on='index', lsuffix='from_second_file ',
                                            how='inner')
        joined_data_frame = joined_data_frame.sort_values('index')
        #joined_data_frame.drop('index', inplace=True, axis=1)
        data = joined_data_frame.to_numpy()
        return data

    def _verify_params_make_sense(k: int, max_iter: int, eps: float, data: List[List[float]]):
        # verify data shape
        N = len(data)
        if N == 0:
            exit_error()
        dims = len(data[0])
        if dims == 0:
            exit_error()
        for point in data:
            if len(point) != dims:
                exit_error()
        if k >= len(datapoints_list):
            exit_invalid_input() # k cannot be as large as or larger than datapoints_list
        if k < 0:
            exit_invalid_input() # it can also not be negative
        if eps < 0:
            exit_invalid_input() # epsilon cannot be negative
        for point in data:
            if not point[0].is_integer():
                exit_error() # first item in every data row must be an index
    
    k, max_iter, eps, file_name_1, file_name_2 = _get_cmd_args()
    _validate_input_filenames(file_name_1, file_name_2)
    datapoints_list = _read_data_as_np(file_name_1, file_name_2)
    _verify_params_make_sense(k, max_iter, eps, datapoints_list)
    return k, max_iter, eps, datapoints_list


def exit_error():
    exit_with_msg(MSG_ERR_GENERIC)


def exit_invalid_input():
    exit_with_msg(MSG_ERR_INVALID_INPUT)


def exit_with_msg(msg: str):
    print(msg)
    exit(1)


if __name__ == '__main__':
    main()
