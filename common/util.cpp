#include "util.h"
#include <cstdio>
namespace fmp {
  Lock::Lock(Mutex *obj, bool access) {
		lock_obj = obj;
		attr = access;
		lock_obj->acquire(attr);
	}
	Lock::Lock(Lock &&copy) {
		lock_obj = copy.lock_obj;
		attr = copy.attr;
		copy.lock_obj = 0;
	}
	Lock &Lock::operator=(Lock &&copy) {
		{
			Mutex *Tmp = lock_obj;
			lock_obj = copy.lock_obj;
			copy.lock_obj = Tmp;
		}
		bool Tmp = attr;
		attr = copy.attr;
		copy.attr = Tmp;
		return *this;
	}
	Lock::~Lock() {
		if (lock_obj) lock_obj->release(attr);
	}

  	ConQueue::ConQueue() {
		last_lock = get_single_mutex();
		last_cond = get_cond_var(last_lock);
		first = nullptr;
		last = nullptr;
		total_bytes = 0;
	}
	ByteArray ConQueue::get_bytes(size_t num_bytes) {
		ByteArray rtn(uint8_t(0), num_bytes);
		get_bytes(rtn, num_bytes, 0);
		return rtn;
	}
	ByteArray ConQueue::try_get_bytes(size_t num_bytes) {
		ByteArray rtn(uint8_t(0), num_bytes);
		rtn.set_length(try_get_bytes(rtn, num_bytes, 0));
		return rtn;
	}
	void ConQueue::put_bytes(const ByteArray &bytes) {
		ByteArray tmp = bytes;
		put_bytes((ByteArray &&)tmp);
	}
	void ConQueue::get_bytes(ByteArray &into, size_t num_bytes, size_t at) {
		bool lock_held = false;
		while (num_bytes) {
			if (!lock_held) {
				last_lock->acquire();
			}
			if (first != last) {
				last_lock->release(); // release to avoid holding the lock for longer than necessary
				lock_held = false;
				if (first->data.length() <= num_bytes) {
					into.write_from_at(first->data, at);
					at += first->data.length();
					num_bytes -= first->data.length();
					atomic_sub(total_bytes, first->data.length());
					QBlk *tmp = first;
					first = first->next;
					delete tmp;
				} else {
					into.write_from_at(first->data, at, at + num_bytes);
					first->data.remove_from_start(num_bytes);
					atomic_sub(total_bytes, num_bytes);
					at += num_bytes;
					num_bytes = 0;
				}
			} else if (first) {
				if (first->data.length() <= num_bytes) {
					into.write_from_at(first->data, at);
					at += first->data.length();
					num_bytes -= first->data.length();
					atomic_sub(total_bytes, first->data.length());
					QBlk *tmp = first;
					last = first = nullptr;
					delete tmp;
				} else {
					into.write_from_at(first->data, at, at + num_bytes);
					first->data.remove_from_start(num_bytes);
					atomic_sub(total_bytes, num_bytes);
					at += num_bytes;
					num_bytes = 0;
				}
				last_lock->release();
				lock_held = false;
			} else {
				last_cond->wait();
				lock_held = true;
			}
		}
		if (lock_held) {
			last_lock->release();
		}
	}
	size_t ConQueue::try_get_bytes(ByteArray &into, size_t num_bytes, size_t at) {
		while (num_bytes) {
			last_lock->acquire();
			if (first != last) {
				last_lock->release(); // release to avoid holding the lock for longer than necessary
				if (first->data.length() <= num_bytes) {
					into.write_from_at(first->data, at);
					at += first->data.length();
					num_bytes -= first->data.length();
					atomic_sub(total_bytes, first->data.length());
					QBlk *tmp = first;
					first = first->next;
					delete tmp;
				} else {
					into.write_from_at(first->data, at, at + num_bytes);
					first->data.remove_from_start(num_bytes);
					atomic_sub(total_bytes, num_bytes);
					at += num_bytes;
					num_bytes = 0;
				}
			} else if (first) {
				if (first->data.length() <= num_bytes) {
					into.write_from_at(first->data, at);
					at += first->data.length();
					num_bytes -= first->data.length();
					atomic_sub(total_bytes, first->data.length());
					QBlk *tmp = first;
					last = first = nullptr;
					delete tmp;
				} else {
					into.write_from_at(first->data, at, at + num_bytes);
					first->data.remove_from_start(num_bytes);
					atomic_sub(total_bytes, num_bytes);
					at += num_bytes;
					num_bytes = 0;
				}
				last_lock->release();
			} else {
				last_lock->release();
				break;
			}
		}
		return at;
	}
	void ConQueue::put_bytes(ByteArray &&bytes) {
		last_lock->acquire();
		size_t num_bytes = bytes.length();
		if (first == nullptr) {
			first = last = new QBlk();
			first->next = nullptr;
			first->data = (ByteArray &&)bytes;
		} else if (first == last) {
			last = new QBlk();
			first->next = last;
			last->data = (ByteArray &&)bytes;
		} else {
			QBlk *prev = last;
			last = new QBlk();
			prev->next = last;
			last->data = (ByteArray &&)bytes;
		}
		atomic_add(total_bytes, num_bytes);
		last_cond->notify_all();
		last_lock->release();
	}
	void ConQueue::clear(size_t num_bytes) {
		last_lock->acquire();
		QBlk *next = first;
		while (next) {
			first = next;
			next = next->next;
			delete first;
		}
		first = nullptr;
		last = nullptr;
		total_bytes = 0;
		last_lock->release();
	}
	size_t ConQueue::length() {
		return total_bytes;
	}
	ConQueue::~ConQueue() {
		last_cond->is_lock_ref = false;
		destroy_cond(last_cond);
		QBlk *Cur = first;
		while (first) {
			Cur = first->next;
			delete first;
			first = Cur;
		}
	}
	
	Mutex::~Mutex() {}
}