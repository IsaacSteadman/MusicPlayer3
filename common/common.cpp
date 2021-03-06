#include <cmath>
#include <cstdio>
#include <exception>
#include "util.h"

const double NormC0 = pow(20.6, 2);
const double NormC1 = pow(12194, 2);
const double NormC2 = pow(107.7, 2);
const double NormC3 = pow(737.9, 2);
const double NormC4 = pow(10, .2);
const double NormC5 = pow(NormC1, 2);

// calculate the human threshold for hearing adjustment coefficient given frequency x in hertz
double calc_hth_adjust_coef(double x) {
    if (x == 0) return 1;
    double a = x * x;
    double n = pow(a + NormC0, 2) * pow(a + NormC1, 2) * (a + NormC2) * (a + NormC3);
    double d = NormC4 * NormC5 * pow(a, 4);
    return n/d;
}

using fmp::swap;

extern "C" FASTMUSICPLAYER_EXPORT void fft(double *data, size_t nn);

void conv_to_doubles(signed short *pcm, double *data, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    data[i] = pcm[2 * i];
    data[2 * i] = pcm[2 * i + 1];
  }
}

// adjust for human threshold for hearing
void adjust_hth(double *arr, size_t num_points, float sample_rate) {
  size_t n2 = num_points >> 1;
  for (size_t x = 1; x < n2; ++x) {
    arr[x] /= calc_hth_adjust_coef(sample_rate * x / num_points);
  }
}

static fmp::ConQueue * volatile raw_data_queue = nullptr;
static fmp::ConQueue * volatile fft_out_queue = nullptr;

#define MAX_BYTES 0x40000

static volatile bool running = false;
static volatile bool thread_running = false;
static volatile bool paused = false;

void post_mix_effect_cb(void *udata, uint8_t *stream, int len) {
  if (!running) return;
  if (paused) return;
  if (raw_data_queue->length() >= MAX_BYTES) return;
  fmp::ByteArray arr;
  arr.take(stream, len);
  raw_data_queue->put_bytes(arr);
  arr.give();
}

void registered_effect_cb(int chan, uint8_t *stream, int len, void *udata) {
  if (!running) return;
  if (paused) return;
  if (raw_data_queue->length() >= MAX_BYTES) return;
  fmp::ByteArray arr;
  arr.take(stream, len);
  raw_data_queue->put_bytes(arr);
  arr.give();
}


bool wait_shutdown() {
  int attempts = 10;
  if (running) return false;
  if (raw_data_queue) {
    while (thread_running && attempts-- > 0) {
      if (raw_data_queue->length() < MAX_BYTES) raw_data_queue->put_bytes(fmp::ByteArray((uint8_t)0, 4096));
      _sleep(10);
    }
  }
  return attempts >= 0;
}

static size_t real_fft_size;
static double real_sample_rate;


extern "C" {
  FASTMUSICPLAYER_EXPORT void set_shutdown_state(bool shutdown) {
    if (!shutdown && !running) {
      while (raw_data_queue);
    }
    running = !shutdown;
  }
  FASTMUSICPLAYER_EXPORT bool fmp_init(size_t fft_size, double sample_rate) {
    if (!wait_shutdown()) return false;
    real_fft_size = fft_size;
    real_sample_rate = sample_rate;
    if (raw_data_queue) delete raw_data_queue;
    if (fft_out_queue) delete fft_out_queue;
    raw_data_queue = new fmp::ConQueue();
    fft_out_queue = new fmp::ConQueue();
    running = true;
  }
  FASTMUSICPLAYER_EXPORT bool fmp_shutdown() {
    set_shutdown_state(true);
    return wait_shutdown();
  }
  FASTMUSICPLAYER_EXPORT void fmp_pause() {
    paused = true;
  }
  FASTMUSICPLAYER_EXPORT void fmp_unpause() {
    paused = false;
  }
  FASTMUSICPLAYER_EXPORT void thread_function() {
    thread_running = true;
    const size_t fft_size = real_fft_size;
    const size_t fft_size2 = fft_size >> 1;
    const double sample_rate = real_sample_rate;
    fmp::ByteArray data_buf{(uint8_t)0, 2 * fft_size * sizeof(int16_t)};
    fmp::Array<double> db_buf{(double)0, 2 * fft_size};
    fmp::ByteArray tmp;
    try {
      while (running) {
        raw_data_queue->get_bytes(data_buf, 2 * fft_size); // receive data for the stereo (dual channel) audio
        conv_to_doubles((int16_t *)data_buf.get_data(), db_buf.get_data(), fft_size);
        double *a = db_buf.get_data();
        double *b = db_buf.get_data() + fft_size;
        fft(a, fft_size2);
        fft(b, fft_size2);
        for (size_t i = 1; i < fft_size2; ++i) {
          size_t j = fft_size - i;
          double x, y;
          x = a[i];
          y = a[j];
          double m = sqrt(x * x + y * y);
          a[i] = m;
          a[j] = atan2(y, x);
          x = b[i];
          y = b[j];
          m = sqrt(x * x + y * y);
          b[i] = m;
          b[j] = atan2(y, x);
        }
        adjust_hth(a, fft_size, sample_rate);
        adjust_hth(b, fft_size, sample_rate);
        double a_max = 0.01;
        double b_max = 0.01;
        for (size_t i = 1; i < fft_size2; ++i) {
          double x = a[i];
          if (x > a_max) a_max = x;
          x = b[i];
          if (x > b_max) b_max = x;
        }
        for (size_t i = 1; i < fft_size2; ++i) {
          a[i] /= a_max;
          b[i] /= b_max;
        }
        tmp.take((uint8_t *)db_buf.get_data(), db_buf.length() * sizeof(double));
        fft_out_queue->put_bytes(tmp);
        tmp.give();
      }
      printf("thread_is_dead reason: stopped running\n");
    } catch (std::exception &ex) {
      printf("thread_is_dead reason: exception\n  %s\n  raw_data_queue = %p\n  raw_data_queue.length() = %i\n", ex.what(), raw_data_queue, raw_data_queue ? raw_data_queue->length() : 0);
    } catch (...) {
      printf("thread_is_dead reason: exception\n  raw_data_queue = %p\n  raw_data_queue.length() = %i\n", raw_data_queue, raw_data_queue ? raw_data_queue->length() : 0);
      tmp.give();
    }
    thread_running = false;
  }
  FASTMUSICPLAYER_EXPORT size_t get_total_bytes_out() {
    return fft_out_queue->length();
  }
  FASTMUSICPLAYER_EXPORT size_t get_expected_out_buf_size() {
    return sizeof(double) * 2 * real_fft_size;
  }
  FASTMUSICPLAYER_EXPORT bool fill_output_buf(double *buf) {
    fmp::ByteArray tmp;
    const size_t size = get_expected_out_buf_size();
    tmp.take((uint8_t *)buf, size);
    size_t at = 0;
    try {
      at = fft_out_queue->try_get_bytes(tmp, size);
      tmp.give();
    } catch (...) {
      tmp.give();
    }
    if (at < size) {
      for (size_t i = at / sizeof(double); i < size / sizeof(double); ++i) {
        buf[i] = 0.0;
      }
    }
    return at > 0;
  }
  FASTMUSICPLAYER_EXPORT void *get_sdl_mixer_post_mix() {
    return post_mix_effect_cb;
  }
  FASTMUSICPLAYER_EXPORT void *get_sdl_mixer_registered() {
    return registered_effect_cb;
  }
  void fft(double* data, size_t nn)
	{
    size_t n, mmax, m, j, istep, i;
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
}