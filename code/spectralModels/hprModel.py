import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import hamming, triang, blackmanharris
from scipy.fftpack import fft, ifft, fftshift

import sys, os, functools, time

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
  

  
def hprModel(x, fs, w, N, t, nH, minf0, maxf0, f0et, maxhd):
  # Analysis/synthesis of a sound using the harmonic plus residual model
  # x: input sound, fs: sampling rate, w: analysis window (odd size), 
  # N: FFT size (minimum 512), t: threshold in negative dB, 
  # nH: maximum number of harmonics, minf0: minimum f0 frequency in Hz, 
  # maxf0: maximim f0 frequency in Hz, 
  # f0et: error threshold in the f0 detection (ex: 5),
  # maxhd: max. relative deviation in harmonic detection (ex: .2)
  # y: output sound, yh: harmonic component, yr: residual component

  hN = N/2                                                      # size of positive spectrum
  hM = (w.size+1)/2                                             # half analysis window size
  Ns = 512                                                      # FFT size for synthesis (even)
  H = Ns/4                                                      # Hop size used for analysis and synthesis
  hNs = Ns/2      
  pin = max(hNs, hM)                                            # initialize sound pointer in middle of analysis window          
  pend = x.size - max(hNs, hM)                                  # last sample to start a frame
  fftbuffer = np.zeros(N)                                       # initialize buffer for FFT
  yhw = np.zeros(Ns)                                            # initialize output sound frame
  yrw = np.zeros(Ns)                                            # initialize output sound frame
  yh = np.zeros(x.size)                                         # initialize output array
  yr = np.zeros(x.size)                                         # initialize output array
  w = w / sum(w)                                                # normalize analysis window
  sw = np.zeros(Ns)     
  ow = triang(2*H);                                             # overlapping window
  sw[hNs-H:hNs+H] = ow      
  bh = blackmanharris(Ns)                                       # synthesis window
  bh = bh / sum(bh)                                             # normalize synthesis window
  wr = bh                                                       # window for residual
  sw[hNs-H:hNs+H] = sw[hNs-H:hNs+H] / bh[hNs-H:hNs+H]

  while pin<pend:       
            
  #-----analysis-----             
    xw = x[pin-hM:pin+hM-1] * w                                  # window the input sound
    fftbuffer = np.zeros(N)                                      # reset buffer
    fftbuffer[:hM] = xw[hM-1:]                                   # zero-phase window in fftbuffer
    fftbuffer[N-hM+1:] = xw[:hM-1]                           
    X = fft(fftbuffer)                                           # compute FFT
    mX = 20 * np.log10( abs(X[:hN]) )                            # magnitude spectrum of positive frequencies
    ploc = PP.peakDetection(mX, hN, t)                
    pX = np.unwrap( np.angle(X[:hN]) )                           # unwrapped phase spect. of positive freq.    
    iploc, ipmag, ipphase = PP.peakInterp(mX, pX, ploc)            # refine peak values
    
    f0 = fd.f0DetectionTwm(iploc, ipmag, N, fs, f0et, minf0, maxf0)  # find f0
    hloc = np.zeros(nH)                                          # initialize harmonic locations
    hmag = np.zeros(nH)-100                                      # initialize harmonic magnitudes
    hphase = np.zeros(nH)                                        # initialize harmonic phases
    hf = (f0>0)*(f0*np.arange(1, nH+1))                          # initialize harmonic frequencies
    hi = 0                                                       # initialize harmonic index
    npeaks = ploc.size;                                          # number of peaks found
    
    while f0>0 and hi<nH and hf[hi]<fs/2 :                       # find harmonic peaks
      dev = min(abs(iploc/N*fs - hf[hi]))
      pei = np.argmin(abs(iploc/N*fs - hf[hi]))                  # closest peak
      if ( hi==0 or not any(hloc[:hi]==iploc[pei]) ) and dev<maxhd*hf[hi] :
        hloc[hi] = iploc[pei]                                    # harmonic locations
        hmag[hi] = ipmag[pei]                                    # harmonic magnitudes
        hphase[hi] = ipphase[pei]                                # harmonic phases
      hi += 1                                                    # increase harmonic index
    
    hloc[:hi] = (hloc[:hi]!=0) * (hloc[:hi]*Ns/N)                # synth. locs
    ri = pin-hNs-1                                               # input sound pointer for residual analysis
    xr = x[ri:ri+Ns]*wr                                          # window the input sound                                       
    fftbuffer = np.zeros(Ns)                                     # reset buffer
    fftbuffer[:hNs] = xr[hNs:]                                   # zero-phase window in fftbuffer
    fftbuffer[hNs:] = xr[:hNs]                           
    Xr = fft(fftbuffer)                                          # compute FFT for residual analysis
  
  #-----synthesis-----
    Yh = GS.genSpecSines(hloc[:hi], hmag, hphase, Ns)               # generate spec sines          
    Yr = Xr-Yh;                                                  # get the residual complex spectrum
    
    fftbuffer = np.zeros(Ns)
    fftbuffer = np.real( ifft(Yh) )                              # inverse FFT
    yhw[:hNs-1] = fftbuffer[hNs+1:]                              # undo zero-phase window
    yhw[hNs-1:] = fftbuffer[:hNs+1] 
    
    fftbuffer = np.zeros(Ns)
    fftbuffer = np.real( ifft(Yr) )
    yrw[:hNs-1] = fftbuffer[hNs+1:]                              # residual in time domain using inverse FFT
    yrw[hNs-1:] = fftbuffer[:hNs+1]
    
    yh[ri:ri+Ns] += sw*yhw                                       # overlap-add for sines
    yr[ri:ri+Ns] += sw*yrw                                       # overlap-add for residual
    pin += H                                                     # advance sound pointer
  
  y = yh+yr
  return y, yh, yr


def defaultTest():
    
    str_time = time.time()
   
    #(fs, x) = wp.wavread('../../sounds/oboe.wav')
    (fs, x) = wp.wavread(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../sounds/oboe.wav'))
    w = np.hamming(1025)
    N = 1024
    t = -120
    nH = 30
    minf0 = 200
    maxf0 = 500
    f0et = 2
    maxhd = 0.2
    y, yh, yr = hprModel(x, fs, w, N, t, nH, minf0, maxf0, f0et, maxhd)
    
    print "time taken for computation " + str(time.time()-str_time)
  
if __name__ == '__main__':
    
    (fs, x) = wp.wavread('../../sounds/oboe.wav')
    w = np.hamming(1025)
    N = 1024
    t = -120
    nH = 30
    minf0 = 200
    maxf0 = 500
    f0et = 2
    maxhd = 0.2
    y, yh, yr = hprModel(x, fs, w, N, t, nH, minf0, maxf0, f0et, maxhd)

    wp.play(y, fs)
    wp.play(yh, fs)
    wp.play(yr, fs)