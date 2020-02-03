#include "../common/util.h"
#include <Windows.h>

namespace fmp {
  DWORD __stdcall thread_proc(void *params) {
    uint32_t Rtn = 0;
    {
      Thread::ThreadParams &parameters = *((Thread::ThreadParams *)params);
      Rtn = parameters.function(parameters.h_thread, parameters.thread_id, parameters.func_params);
    }
    delete params;
    return Rtn;
  }
  Thread::Thread() {
    h_thread = 0;
    thread_id = 0;
  }
  Thread::Thread(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params) {
    ThreadParams &params = *(new ThreadParams);
    params.function = thread_func;
    params.func_params = func_params;
    {
      SECURITY_ATTRIBUTES security_attrib;
      security_attrib.bInheritHandle = TRUE;
      security_attrib.lpSecurityDescriptor = NULL;
      security_attrib.nLength = sizeof(SECURITY_ATTRIBUTES);
      h_thread = CreateThread(&security_attrib, NULL, thread_proc, &params, CREATE_SUSPENDED, (LPDWORD)&thread_id);
      params.h_thread = h_thread;
      params.thread_id = thread_id;
      ResumeThread(HANDLE(h_thread));
    }
  }
  Thread::Thread(uint32_t thread_id) {
    this->thread_id = thread_id;
    if (thread_id != 0) h_thread = OpenThread(THREAD_ALL_ACCESS, TRUE, thread_id);
    else h_thread = 0;
  }
  Thread &Thread::operator=(Thread &&copy) {
    h_thread = copy.h_thread;
    thread_id = copy.thread_id;
    copy.h_thread = 0;
    copy.thread_id = 0;
    return (*this);
  }
  Thread &Thread::operator=(const Thread &copy) {
    thread_id = copy.thread_id;
    DuplicateHandle(GetCurrentProcess(), copy.h_thread, GetCurrentProcess(),
      &(HANDLE)h_thread, THREAD_ALL_ACCESS, TRUE, DUPLICATE_SAME_ACCESS);
    return *this;
  }
  void Thread::init(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params) {
    ThreadParams &params = *(new ThreadParams);
    params.function = thread_func;
    params.func_params = func_params;
    {
      SECURITY_ATTRIBUTES security_attrib;
      security_attrib.bInheritHandle = TRUE;
      security_attrib.lpSecurityDescriptor = NULL;
      security_attrib.nLength = sizeof(SECURITY_ATTRIBUTES);
      h_thread = CreateThread(&security_attrib, NULL, thread_proc, &params, CREATE_SUSPENDED, (LPDWORD)&thread_id);
      params.h_thread = h_thread;
      params.thread_id = thread_id;
      ResumeThread(HANDLE(h_thread));
    }
  }
  void Thread::set_thread(uint32_t id) {
    if (h_thread != 0) CloseHandle((HANDLE)h_thread);
    thread_id = id;
    if (id != 0) h_thread = OpenThread(THREAD_ALL_ACCESS, TRUE, id);
    else h_thread = 0;
  }
  void Thread::make_current_thread() {
    HANDLE h_threadTemp = GetCurrentThread();
    DuplicateHandle(GetCurrentProcess(), h_threadTemp, GetCurrentProcess(),
      &(HANDLE)h_thread, THREAD_ALL_ACCESS, TRUE, DUPLICATE_SAME_ACCESS);
    thread_id = GetCurrentThreadId();
  }
  bool Thread::suspend() {
    if (h_thread == 0) return false;
    SuspendThread(HANDLE(h_thread));
    return true;
  }
  bool Thread::resume() {
    if (h_thread == 0) return false;
    ResumeThread(HANDLE(h_thread));
    return true;
  }
  bool Thread::join() {
    if (GetCurrentThreadId() == thread_id) return false;
    return WaitForSingleObject(h_thread, INFINITE) != 0xFFFFFFFF;
  }
  bool Thread::exit_this_thread(uint32_t exit_code) {
    if (h_thread == 0) return false;
    ExitThread(exit_code);
  }
  bool Thread::terminate(uint32_t exit_code) {
    if (h_thread == 0) return false;
    TerminateThread(HANDLE(h_thread), exit_code);
    return true;
  }
  bool Thread::is_this_thread() {
    return thread_id == GetCurrentThreadId();
  } // Is the thread that the object represents the same as the thread that called this function
  Thread::~Thread() {
    if (h_thread != 0) CloseHandle((HANDLE)h_thread);
  }


  void atomic_inc(uint32_t &num) {
    InterlockedIncrement(&num);
  }
  void atomic_inc(uint64_t &num) {
    InterlockedIncrement(&num);
  }
  void atomic_dec(uint32_t &num) {
    InterlockedDecrement(&num);
  }
  void atomic_dec(uint64_t &num) {
    InterlockedDecrement(&num);
  }
  void atomic_add(uint32_t &num, uint32_t add) {
    InterlockedExchangeAdd(&num, add);
  }
  void atomic_add(uint64_t &num, uint64_t add) {
    InterlockedExchangeAdd(&num, add);
  }
  void atomic_sub(uint32_t &num, uint32_t add) {
    add -= 1;
    add = ~add;
    InterlockedExchangeAdd(&num, add);
  }
  void atomic_sub(uint64_t &num, uint64_t add) {
    add -= 1;
    add = ~add;
    InterlockedExchangeAdd(&num, add);
  }


  class SingleMutex : public Mutex {
  public:
    CRITICAL_SECTION data;
    SingleMutex();
    bool try_acquire(bool access);
    void acquire(bool access);
    void release(bool access);
    size_t get_type();
    ~SingleMutex();
  };
  SingleMutex::SingleMutex() {
    InitializeCriticalSection(&data);
  }
  bool SingleMutex::try_acquire(bool access) {
    return TryEnterCriticalSection(&data) != 0;
  }
  void SingleMutex::acquire(bool access) {
    EnterCriticalSection(&data);
  }
  void SingleMutex::release(bool access) {
    LeaveCriticalSection(&data);
  }
  size_t SingleMutex::get_type() {
    return 1;
  }
  SingleMutex::~SingleMutex() {
    DeleteCriticalSection(&data);
  }
  class RWMutex : public Mutex {
  public:
    SRWLOCK data;
    RWMutex();
    bool try_acquire(bool access);
    void acquire(bool access);
    void release(bool access);
    size_t get_type();
    ~RWMutex();
  };
  RWMutex::RWMutex() {
    InitializeSRWLock(&data);
  }
  bool RWMutex::try_acquire(bool access) {
    return (access ? TryAcquireSRWLockExclusive(&data) : TryAcquireSRWLockShared(&data)) != 0;
  }
  void RWMutex::acquire(bool access) {
    if (access) AcquireSRWLockExclusive(&data);
    else AcquireSRWLockShared(&data);
  }
  void RWMutex::release(bool access) {
    if (access) ReleaseSRWLockExclusive(&data);
    else ReleaseSRWLockShared(&data);
  }
  size_t RWMutex::get_type() {
    return 2;
  }
  RWMutex::~RWMutex() {}
  Mutex *get_single_mutex() {
    return new SingleMutex();
  }
  Mutex *get_rw_mutex() {
    return new RWMutex();
  }
  void destroy_mutex(Mutex *obj) {
    delete obj;
  }
  void destroy_cond(CondVar *obj) {
    delete obj;
  }
  CondVar::~CondVar() {}
  class RWCondVar : public CondVar {
  private:
    CONDITION_VARIABLE data;
    RWMutex *rw_lock;
    size_t num_waiting;
    size_t num_allow_wake;
    SingleMutex inf_lock;
  public:
    RWCondVar(RWMutex *the_lock);
    void notify();
    void notify_all();
    void wait(uint32_t timeout = MAX_INT32, bool access = false);
    Mutex *get_intern_lock();
    ~RWCondVar();
  };
  RWCondVar::RWCondVar(RWMutex *the_lock) {
    is_lock_ref = true;
    pre_wait_notify = false;
    num_waiting = 0;
    num_allow_wake = 0;
    rw_lock = the_lock;
    InitializeConditionVariable(&data);
  }
  void RWCondVar::notify() {
    inf_lock.acquire(false);
    if (pre_wait_notify) num_allow_wake += 1;
    else if (num_waiting > 0 && num_allow_wake < num_waiting) num_allow_wake += 1;
    inf_lock.release(false);
    WakeConditionVariable(&data);
  }
  void RWCondVar::notify_all() {
    inf_lock.acquire(false);
    num_allow_wake = num_waiting;
    inf_lock.release(false);
    WakeAllConditionVariable(&data);
  }
  void RWCondVar::wait(uint32_t timeout, bool access) {
    inf_lock.acquire(false);
    ++num_waiting;
    while (true) {
      if (num_allow_wake) break;
      inf_lock.release(false);
      SleepConditionVariableSRW(&data, &rw_lock->data, timeout, access ? 0 : (CONDITION_VARIABLE_LOCKMODE_SHARED));
      inf_lock.acquire(false);
    }
    --num_allow_wake;
    --num_waiting;
    inf_lock.release(false);
  }
  Mutex *RWCondVar::get_intern_lock() {
    return rw_lock;
  }
  RWCondVar::~RWCondVar() {
    if (!is_lock_ref) destroy_mutex(rw_lock);
  }
  class CSCondVar : public CondVar {
  private:
    CONDITION_VARIABLE data;
    SingleMutex *cs_lock;
    size_t num_waiting;
    size_t num_allow_wake;
  public:
    CSCondVar(SingleMutex *the_lock);
    void notify();
    void notify_all();
    void wait(uint32_t timeout = MAX_INT32, bool access = false);
    Mutex *get_intern_lock();
    ~CSCondVar();
  };
  CSCondVar::CSCondVar(SingleMutex *the_lock) {
    is_lock_ref = true;
    pre_wait_notify = false;
    num_waiting = 0;
    num_allow_wake = 0;
    cs_lock = the_lock;
    InitializeConditionVariable(&data);
  }
  void CSCondVar::notify() {
    if (pre_wait_notify) atomic_inc(num_allow_wake);
    else if (num_waiting > 0 && num_allow_wake < num_waiting) atomic_inc(num_allow_wake);
    WakeConditionVariable(&data);
  }
  void CSCondVar::notify_all() {
    num_allow_wake = num_waiting;
    WakeAllConditionVariable(&data);
  }
  void CSCondVar::wait(uint32_t timeout, bool access) {
    atomic_inc(num_waiting);
    while (num_allow_wake == 0) SleepConditionVariableCS(&data, &cs_lock->data, timeout);
    atomic_dec(num_allow_wake);
    atomic_dec(num_waiting);
  }
  Mutex *CSCondVar::get_intern_lock() {
    return cs_lock;
  }
  CSCondVar::~CSCondVar() {
    if (!is_lock_ref) destroy_mutex(cs_lock);
  }
  CondVar *get_cond_var(Mutex *the_lock) {
    if (the_lock == 0)
    {
      CondVar *rtn = new CSCondVar(new SingleMutex());
      rtn->is_lock_ref = false;
    }
    switch (the_lock->get_type()) {
    case 1:
      return new CSCondVar((SingleMutex *)the_lock);
    case 2:
      return new RWCondVar((RWMutex *)the_lock);
    default:
      return 0;
    }
  }

  /* void ConQueue::chg_bytes(size_t amt, bool is_add) {
    if (!is_add)
    {
      amt ^= amt;
      amt += 1;
    }
#if defined(_WIN64)
    InterlockedExchangeAdd64((ptrdiff_t *)&total_bytes, (ptrdiff_t)amt);
#else
    InterlockedExchangeAdd((ptrdiff_t *)&total_bytes, (ptrdiff_t)amt);
#endif
  }*/
}