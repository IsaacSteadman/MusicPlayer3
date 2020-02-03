#include "fmp_base.h"
#define MAX_INT32 0xFFFFFFFF
namespace fmp {
  class FASTMUSICPLAYER_EXPORT Thread {
  public:
    void *h_thread;
    uint32_t thread_id;
    struct ThreadParams {
      void *h_thread;
      uint32_t thread_id;
      uint32_t(*function)(void *, uint32_t, void *);
      void *func_params;
    };
    Thread();
    Thread(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params);
    Thread(uint32_t thread_id);
    Thread &operator=(Thread &&copy);
    Thread &operator=(const Thread &copy);
    void init(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params);
    void set_thread(uint32_t id);
    void make_current_thread();
    bool suspend();
    bool resume();
    bool join();
    bool exit_this_thread(uint32_t exit_code = 0);
    bool terminate(uint32_t exit_code = 0);
    bool is_this_thread(); // Is the thread that the object represents the same as the thread that called this function
    ~Thread();
  };
  class FASTMUSICPLAYER_EXPORT Mutex {
  public:
    enum Access {
      ACCESS_READ = 0,
      ACCESS_WRITE = 1,
      ACCESS_QUICK = 2
    };
    //access true for write
    virtual bool try_acquire(bool access = false) = 0;
    //access true for write
    virtual void acquire(bool access = false) = 0;
    //access true for write
    virtual void release(bool access = false) = 0;
    virtual size_t get_type() = 0;
    virtual ~Mutex();
  };
  class FASTMUSICPLAYER_EXPORT CondVar {
  public:
    bool is_lock_ref;
    bool pre_wait_notify;//Allow notifies to affect waits later on NOTE: only works on single notifies
    virtual void notify() = 0;
    virtual void notify_all() = 0;
    virtual void wait(uint32_t timeout = MAX_INT32, bool access = false) = 0;
    virtual Mutex *get_intern_lock() = 0;
    virtual ~CondVar();
  };
  FASTMUSICPLAYER_EXPORT CondVar *get_cond_var(Mutex *TheLock = 0);
  FASTMUSICPLAYER_EXPORT Mutex *get_single_mutex();
  FASTMUSICPLAYER_EXPORT Mutex *get_rw_mutex();
  FASTMUSICPLAYER_EXPORT void destroy_mutex(Mutex *obj);
  FASTMUSICPLAYER_EXPORT void destroy_cond(CondVar *obj);
  class FASTMUSICPLAYER_EXPORT Lock {
  private:
    bool attr;
    Mutex *lock_obj;
  public:
    Lock(Mutex *obj, bool access = false);
    Lock(Lock &&copy);
    Lock &operator=(Lock &&copy);
    ~Lock();
  };
  FASTMUSICPLAYER_EXPORT void atomic_inc(uint32_t &num);
  FASTMUSICPLAYER_EXPORT void atomic_inc(uint64_t &num);
  FASTMUSICPLAYER_EXPORT void atomic_dec(uint32_t &num);
  FASTMUSICPLAYER_EXPORT void atomic_dec(uint64_t &num);
  FASTMUSICPLAYER_EXPORT void atomic_add(uint32_t &num, uint32_t add);
  FASTMUSICPLAYER_EXPORT void atomic_add(uint64_t &num, uint64_t add);
  FASTMUSICPLAYER_EXPORT void atomic_sub(uint32_t &num, uint32_t add);
  FASTMUSICPLAYER_EXPORT void atomic_sub(uint64_t &num, uint64_t add);
}
