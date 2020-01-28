#include <cmath>
#ifdef __linux__
#define FASTMUSICPLAYER_EXPORT
#else
#define FASTMUSICPLAYER_EXPORT __declspec(dllexport)
#endif
#ifndef M_PI
#define M_PI 3.141592653589793238462643383279
#endif

double normalizer(double x) {
  if (x == 0) {
    return 1;
  }
  a = pow(x, 2);
  n = pow(a + pow(20.6, 2), 2) * pow(a + pow(12194, 2), 2) * (a + pow(107.7, 2)) * (a + pow(737.9, 2));
  d = pow(10, .2) * pow(12194, 4) * pow(x, 8);
  return n / d;
}


extern "C" {
  FASTMUSICPLAYER_EXPORT void fft(double* data, unsigned long nn)
	{
    unsigned long n, mmax, m, j, istep, i;
    double wtemp, wr, wpr, wpi, wi, theta;
    double tempr, tempi;

    // reverse-binary reindexing
    n = nn<<1;
    j=1;
    for (i=1; i<n; i+=2) {
      if (j>i) {
        swap(data[j-1], data[i-1]);
        swap(data[j], data[i]);
      }
      m = nn;
      while (m>=2 && j>m) {
        j -= m;
        m >>= 1;
      }
      j += m;
    };

    // here begins the Danielson-Lanczos section
    mmax=2;
    while (n>mmax) {
      istep = mmax<<1;
      theta = -(2*M_PI/mmax);
      wtemp = sin(0.5*theta);
      wpr = -2.0*wtemp*wtemp;
      wpi = sin(theta);
      wr = 1.0;
      wi = 0.0;
      for (m=1; m < mmax; m += 2) {
        for (i=m; i <= n; i += istep) {
          j=i+mmax;
          tempr = wr*data[j-1] - wi*data[j];
          tempi = wr * data[j] + wi*data[j-1];

          data[j-1] = data[i-1] - tempr;
          data[j] = data[i] - tempi;
          data[i-1] += tempr;
          data[i] += tempi;
        }
        wtemp=wr;
        wr += wr*wpr - wi*wpi;
        wi += wi*wpr + wtemp*wpi;
      }
      mmax=istep;
    }
	}
  FASTMUSICPLAYER_EXPORT void normalize_human(double *arr, unsigned long nFft, float sampleRate) {
    for (unsigned long x = 0; x < nFft; ++x) {
      arr[x] /= normalizer(sampleRate * x / (nFft << 1));
    }
  }
}