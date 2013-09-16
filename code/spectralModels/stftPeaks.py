import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import hamming
from scipy.fftpack import fft, ifft
import time

import sys, os

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../basicFunctions/'))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../basicFunctions_C/'))

#sys.path.append(os.path.realpath('../basicFunctions/'))
#sys.path.append(os.path.realpath('../basicFunctions_C/'))
import smsF0DetectionTwm as fd
import smsWavplayer as wp
import smsPeakProcessing as PP

try:
  import basicFunctions_C as GS
except ImportError:
  import smsGenSpecSines as GS
  print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
  print "NOTE: Cython modules for some functions were not imported, the processing will be slow"
  print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
  

def stftPeaks(x, fs, w, N, H, t) :
  # Analysis/synthesis of a sound using the peaks
  # x: input array sound, w: analysis window, N: FFT size, H: hop size, 
  # t: threshold in negative dB, y: output sound

  hN = N/2                                                # size of positive spectrum
  hM = (w.size+1)/2                                       # half analysis window size
  pin = hM                                                # initialize sound pointer in middle of analysis window       
  pend = x.size-hM                                        # last sample to start a frame
  fftbuffer = np.zeros(N)                                 # initialize buffer for FFT
  yw = np.zeros(w.size)                                   # initialize output sound frame
  y = np.zeros(x.size)                                    # initialize output array
  w = w / sum(w)                                          # normalize analysis window
  
  while pin<pend:       
           
  #-----analysis-----             
    xw = x[pin-hM:pin+hM-1] * w                           # window the input sound
    fftbuffer = np.zeros(N)                               # reset buffer
    fftbuffer[:hM] = xw[hM-1:]                            # zero-phase window in fftbuffer
    fftbuffer[N-hM+1:] = xw[:hM-1]        
    X = fft(fftbuffer)                                    # compute FFT
    mX = 20 * np.log10( abs(X[:hN]) )                     # magnitude spectrum of positive frequencies
    ploc = PP.peakDetection(mX, hN, t)
    pmag = mX[ploc]
    # freq = np.arange(0, fs/2, fs/N)                     # frequency axis in Hz
    # freq = freq[:freq.size-1]
    # fig.clf()
    # plt.plot(freq, mX)
    # plt.ylabel('Magnitude(dB)'), plt.xlabel('Frequency(Hz)')         
    # plt.plot(freq[ploc], pmag, 'ro')
    # plt.draw()          
    pX = np.unwrap( np.angle(X[:hN]) )                    # unwrapped phase spect. of positive freq.
    pphase = pX[ploc]

  #-----synthesis-----
    Y = np.zeros(N, dtype = complex)
    Y[ploc] = 10**(pmag/20) * np.exp(1j*pphase)           # generate positive freq.
    Y[N-ploc] = 10**(pmag/20) * np.exp(-1j*pphase)        # generate neg.freq.
    fftbuffer = np.real( ifft(Y) )                        # inverse FFT
    yw[:hM-1] = fftbuffer[N-hM+1:]                        # undo zero-phase window
    yw[hM-1:] = fftbuffer[:hM] 
    y[pin-hM:pin+hM-1] += H*yw                            # overlap-add
    pin += H                                              # advance sound pointer
  
  return y


def defaultTest():
    
    str_time = time.time()
      
    (fs, x) = wp.wavread(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../sounds/oboe.wav'))
    w = np.hamming(511)
    N = 512
    H = 256
    t = -60
    # fig = plt.figure()
    y = stftPeaks(x, fs, w, N, H, t)
    print "time taken for computation " + str(time.time()-str_time)
    
  
if __name__ == '__main__':   
      
    (fs, x) = wp.wavread('../../sounds/oboe.wav')
    wp.play(x, fs)
    w = np.hamming(511)
    N = 512
    H = 256
    t = -60
    # fig = plt.figure()
    y = stftPeaks(x, fs, w, N, H, t)
    wp.play(y, fs)