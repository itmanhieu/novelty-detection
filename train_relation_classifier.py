# This code trains a classifier to distinguish classes that are in, not in, have relatives
# in, or have a parent in imagenet. The feature vectors are the frequencies of the top n
# labels of a particular class
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from sklearn.utils.multiclass import unique_labels
from tqdm import tqdm

def get_feature_vec_top_labels(data, query, n):
	'''
	Creates and returns a feature vector of length n
	The feature vector is based on the distribution of top labels for a class
	If there are not n labels, then zeros are appended to the front of the feature vector
		to make it length n
	'''
	
	grp = query['Biological Group']
	name = query['Class']
	counts = data[grp][name]['counts']
	confs = data[grp][name]['confs']
	# Feature vector of frequencies:
	feat_vec = counts		# Create feature vector

	if feat_vec is None:
		return None

	feat_vec = np.array(feat_vec)
	feat_vec /= sum(feat_vec)		# convert count to frequency

	feat_vec = feat_vec * confs	# Multiply frequencies by confidence levels

	if len(feat_vec) < n:
		feat_vec = np.concatenate((np.zeros(n-len(feat_vec)), feat_vec))

	assert(len(feat_vec[-n:])==n)
	return list(feat_vec[-n:])

def plot_confusion_matrix(y_true, y_pred, classes,
                          normalize=False,
                          title=None,
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if not title:
        if normalize:
            title = 'Normalized confusion matrix'
        else:
            title = 'Confusion matrix, without normalization'

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
    # classes = classes[unique_labels(y_true, y_pred)]
    classes = np.unique(y_true)
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    fig, ax = plt.subplots()
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
    ax.figure.colorbar(im, ax=ax)
    # We want to show all ticks...
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           # ... and label them with the respective list entries
           xticklabels=classes, yticklabels=classes,
           title=title,
           ylabel='True label',
           xlabel='Predicted label')

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    plt.show()
    return ax

if __name__ == '__main__':
	# Load dataframe of inaturalist annotations
	df = pd.read_csv('in_out_class.csv')

	labeled_data = df[df['Biological Group']=='Aves']
	labeled_data = labeled_data[labeled_data['Annotator'].notnull()]

	# Collect feature vectors and labels
	n = 20
	X = []
	Y = []
	XClasses = []
	img_names = []

	'''
	### Uses distribution of top n labels as feature vectors
	with open('alexnet_inat_results/inat_results_top_choice.json', 'r') as f:
		f = json.load(f)
		
		for i in labeled_data.index:
			row = df.iloc[i]
			vec = get_feature_vec_top_labels(f, row, n)
			if vec is None:
				continue
			X.append(list(vec))
			Y.append(row['Relation to Imagenet'])
	'''

	### Uses confidence vectors as feature vectors - looks at separate files, not large json
	for i in labeled_data.index:
		row = df.iloc[i]
		grp = row['Biological Group']
		name = row['Class']
		filename = os.getcwd() + '/alexnet_inat_results/' + grp + '/' + name + '.json'
		with open(filename, 'r') as f:
			f = json.load(f)
			for im in tqdm(f.keys()):		# Loop through the images in the file
				# Query the vector of labels and confidence levels for each image test
				try:
					l = f[im]['labels']
					c = f[im]['confs']
				except:
					print('No label for ', filename, im)

				# Sort according to the label name (alphabetical)
				to_sort = np.argsort(l)
				l_sorted = [l[i] for i in to_sort]
				c_sorted = [c[i] for i in to_sort]
			
				# Add to training data
				X.append(list(c_sorted))
				Y.append(row['Relation to Imagenet'])
				XClasses.append(i)
				img_names.append(im)

	classIDs = np.unique(XClasses)

	X = np.array(X)
	Y = np.array(Y)
	print(X.shape, Y.shape)
	# Split the data
	# X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.33, random_state=42)	# Split by image
	X_train_ids, X_test_ids, Y_train_ids, Y_test_ids = train_test_split(classIDs, classIDs, test_size=0.33, random_state=42)		# Split by class
	X_train = []
	X_test = []
	Y_train = []
	Y_test = []
	train_imgs = []
	test_imgs = []
	for idx in X_train_ids:	# For each class, save the features in X and labels in Y
		im_idxs = np.where(XClasses==idx)
		for i in im_idxs[0]:
			X_train.append(X[i])
			Y_train.append(Y[i])
			train_imgs.append(img_names[i])
	for idx in X_test_ids:	# For each class, save the features in X and labels in Y
		im_idxs = np.where(XClasses==idx)
		for i in im_idxs[0]:
			X_test.append(X[i])
			Y_test.append(Y[i])
			test_imgs.append(img_names[i])

	print(len(X_train), len(X_train[0]), len(Y_train))
	assert(len(test_imgs) == len(X_test) and len(train_imgs) == len(X_train))

	# Train linear classifier
	clf_svc = SVC(tol=1e-3, random_state=True)
	clf_svc.fit(X_train, Y_train)
	preds_svc = clf_svc.predict(X_test)
	print('SVM:', clf_svc.score(X_test, Y_test))

	# Save SVM results:
	path = 'C:/Users/noam_/Documents/Cornell/CS7999/11_18_19/split by class/'
	with open(path+'aves_svm_results.txt', 'w') as f:
		f.write('ImageID\t Actual\t Prediction\n')
		for i, p in enumerate(preds_svc):
			line = test_imgs[i]+'\t'+Y_test[i]+'\t'+p+'\n'
			f.write(line)

	# Train Random Forest Classifier
	clf_rf = RandomForestClassifier(n_estimators=100)
	clf_rf.fit(X_train, Y_train)
	preds_rf = clf_rf.predict(X_test)
	print('Random Forest:', clf_rf.score(X_test, Y_test))
	
	# Save RF results:
	with open(path+'aves_rf_results.txt', 'w') as f:
		f.write('ImageID\t Actual\t Prediction\n')
		for i, p in enumerate(preds_rf):
			line = test_imgs[i]+'\t'+Y_test[i]+'\t'+p+'\n'
			f.write(line)

	# Plot confusion matrices
	classes = ['relative in imagenet', 'in imagenet', 'parent in imagenet', 'not in imagenet']
	title = 'CM for SVM, features=1000 len. conf. vector per image'
	plot_confusion_matrix(Y_test, preds_svc, classes, normalize=True, title=title)
	title = 'CM for RF, features=1000 len. conf. vector per image'
	plot_confusion_matrix(Y_test, preds_rf, classes, normalize=True, title=title)
	