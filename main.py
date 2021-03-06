from joblib import Parallel, delayed
import multiprocessing
import time
import copy
import os.path
from numpy import linalg as LA
import numpy as np
import joblib
import sys
import my_solver as ms
# reload(ms)
import glob

if __name__ == '__main__':
	start_time=time.clock()    
	bFlag = 0
    #initialize parameters
	num_cores = multiprocessing.cpu_count()	
	print ('Num of threads: %s'%num_cores)
	num_iter = 20
	h = int(sys.argv[1]) # h parameter
	d = 3209             # initial (high) dimension 
	csv_path = sys.argv[3] # path of the dataset files (.csv files)
	# filelist = glob.glob(os.path.join(csv_path,'*.csv'))
	# coords = [np.array(os.path.basename(x).replace('.csv','').split(',')).astype(float) for x in filelist]
	# coords = [(-29.5,144.5), (-29.5,145.5), (-29.5,147.5), (-30.5,143.5), (29.5, 115.5), (29.5, 112.5), (29.5, 113.5)] # array with the coordinates in tuple format (lat, lon)#
	coords = joblib.load('./coords.pkl')
	m = len(coords)  # number of tasks, i.e., locations 
	outp = sys.argv[4] # outpath
	varfile = sys.argv[5] # .txt file with the variable names
	remove_ind_file = sys.argv[6] # .pkl file with the indices of the unused input features
	if not os.path.exists(outp+'h_%s_l_%s'%(h,sys.argv[2])): # create a folder for the results
		os.makedirs(outp+'h_%s_l_%s'%(h,sys.argv[2]))
	outpath = outp+'h_%s_l_%s'%(h,sys.argv[2]) # this is the final output folder
	Th = np.random.rand(h,d) # random initialiization of the Th matrix
	u_array = np.zeros((d, m))
	W = np.random.rand(d,m)
	lambd = np.empty((1,m))
	lambd[0,:] = float(sys.argv[2]) # the lambdas are given by the user
    # main loop
	for it in range(num_iter): 
		print('iter: %s'%it)
		w_array = []
		v_array = []
		lambdas = []
		W_old = copy.deepcopy(W)
        # run the optimization problem for each location (in parallel)
		results = Parallel(n_jobs=num_cores)(delayed(ms.solver)(csv_path, coords[i], W, Th, u_array, lambd, i, h, varfile, remove_ind_file) for i in range(m))
		for i in range(len(results)): # keep the results from the previous step
			optDetails, theta, v, l  = results[i]
			w, funcVal, details = optDetails
			w = w[:,np.newaxis]
			w_array.append(w)
			v_array.append(v)
			lambdas.append(l)
        # concatenate the results for all the locations
		w_array_c = np.concatenate((w_array), axis=1)
		v_array_c = np.concatenate((v_array), axis=0)
		u_array = w_array_c + np.dot(np.transpose(theta), np.transpose(v_array_c)) # calculate the u parameters (u = w + Th . v)
		#do the SVD
		U = np.sqrt(np.asarray(lambdas))*u_array
		V1, D, V2 = np.linalg.svd(U)
		V1T = np.transpose(V1)
		Th_old = copy.deepcopy(Th) # keep the previous value
		Th = V1T[:h,:] # make the update
		W = w_array_c
		delta_Theta = Th - Th_old # calculate the difference between the old and the updated values
		delta_W = W - W_old

		r_sum = (np.power(LA.norm(delta_W, 'fro'),2) + np.power(LA.norm(delta_Theta, 'fro'),2))/float(2) # quantify the difference after the updates
		#print(np.power(LA.norm(delta_Theta, 'fro'),2))
		if (r_sum <=0.01): 
			bFlag=1 #% if the updated values are not that different from the ones of the previous step, stop
			break
        # store the results
		joblib.dump(v_array_c, os.path.join(outpath,'v_h_%s_l_%s_iter3.pkl'%(h,sys.argv[2])))
		joblib.dump(w_array_c, os.path.join(outpath,'w_h_%s_l_%s_iter3.pkl'%(h,sys.argv[2])))
		joblib.dump(Th_old, os.path.join(outpath,'theta_h_%s_l_%s_iter3.pkl'%(h,sys.argv[2])))
		joblib.dump(u_array, os.path.join(outpath,'u_h_%s_l_%s_iter3.pkl'%(h,sys.argv[2])))

	end_time=time.clock()    
	if bFlag:
		print ('Convergence!')
	else:
		print ('Maximum num of iterations reached. Exit...')  

	print('Total time: ', (end_time - start_time)/60.0, ' minutes.') 