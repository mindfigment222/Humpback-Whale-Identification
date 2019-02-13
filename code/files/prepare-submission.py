from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tqdm import tqdm
import numpy as np
import pandas as pd
from globals import *
from feature_generator import FeatureGen
from score_generator import ScoreGen
from keras.models import load_model
from utils import load_pickle_file, save_to_pickle
import time
from model import Model
import argparse

def prepare_submission(threshold, filename, score, known, submit):
    """
    Generate kaggle submission file.
    @param threshold: threshold given to 'new_whale'
    @param filname: submission file name
    """
    img2ws = load_pickle_file(img_to_whales)

    new_whale = 'new_whale'
    with open(callback_path + 'score.txt', 'w+') as sf:
        with open(filename, 'wt', newline='\n') as f:
            f.write('Image,Id\n')
            for i, p in enumerate(tqdm(submit)):
                t = []
                s = set()
                a = score[i,:]
                probs = []
                for j in list(reversed(np.argsort(a))):
                    img = known[j]
                    if a[j] < threshold and new_whale not in s:
                        s.add(new_whale)
                        t.append(new_whale)
                        probs.append(a[j])
                        if len(t) == 5:
                            break
                    for w in img2ws[img]:
                        assert w != new_whale
                        if w not in s:
                            s.add(w)
                            t.append(w)
                            probs.append(a[j])
                            if len(t) == 5:
                                break
                    if len(t) == 5:
                        break
                assert len(t) == 5 and len(s) == 5
                f.write(p + ',' + ' '.join(t[:5]) + '\n')
                sf.write(p + ',' + ' '.join(map(str, probs)) + '\n')


def parse_args():
    parser = argparse.ArgumentParser(description='hwi')
    parser.add_argument('--output', '-o', dest='output_filename',
                        help='output filename (.csv)',
                        default=None, type=str)
    parser.add_argument('--model', '-m', dest='model_filename',
                        help='model filename (.h5)',
                        default=None, type=str)
    parser.add_argument('--threshold', '-th', dest='threshold',
                        help='threshold for new_whale',
                        default=0.99, type=float)
    return parser.parse_args()
    
def main():
    tic = time.time()

    known = load_pickle_file(known_file)
    submit = load_pickle_file(submit_file)

    print('inference HWI')
    args = parse_args()
    model_path = models_path + args.model_filename
    submission_path = output_path + args.output_filename
    threshold = args.threshold

    # Load model
    weights = load_model(model_path).get_weights()
    model = Model(0, 0, 'submission')
    model.model.set_weights(weights)

    # Evaluate model
    fknown = model.branch_model.predict_generator(FeatureGen(known, model.img_gen.read_for_testing), max_queue_size=20, workers=8, verbose=0)
    fsubmit = model.branch_model.predict_generator(FeatureGen(submit, model.img_gen.read_for_testing), max_queue_size=20, workers=8, verbose=0)
    score = model.head_model.predict_generator(ScoreGen(fknown, fsubmit), max_queue_size=20, workers=8, verbose=0)
    score = model.score_reshape(score, fknown, fsubmit)

    # Generate submission file
    prepare_submission(threshold, submission_path, score, known, submit)
    toc = time.time()
    print("Inference time: ", (toc - tic) / 60, 'mins')



if __name__ == "__main__":
    main()
    
