#include "../common/fmp_thread.h"

namespace fmp {
    uint32_t thread_proc(void *params) {
		uint32_t Rtn = 0;
		{
			Thread::ThreadParams &parameters = *((Thread::ThreadParams *)params);
			Rtn = parameters.function(parameters.h_thread, parameters.thread_id, parameters.func_params);
		}
		delete params;
		return Rtn;
	}
    Thread::Thread() {
        ;
    }
    Thread::Thread(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params) {
        ;
    }
    Thread::Thread(uint32_t thread_id) {
        ;
    }
    Thread &Thread::operator=(Thread &&copy) {
        ;
    }
    Thread &Thread::operator=(const Thread &copy) {
        ;
    }
    void Thread::init(uint32_t(*thread_func)(void *, uint32_t, void *), void *func_params) {
        ;
    }
    void Thread::set_thread(uint32_t id) {
        ;
    }
    void Thread::make_current_thread() {
        ;
    }
    bool Thread::suspend() {
        ;
    }
    bool Thread::resume() {
        ;
    }
    bool Thread::join() {
        ;
    }
    bool Thread::exit_this_thread(uint32_t exit_code = 0) {
        ;
    }
    bool Thread::terminate(uint32_t exit_code = 0) {
        ;
    }
    bool Thread::is_this_thread() {
        ;
    } // Is the thread that the object represents the same as the thread that called this function
    Thread::~Thread() {
        ;
    }
}