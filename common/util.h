#include "fmp_thread.h"
#include "TemplateUtils.h"
namespace fmp {
	// this is a semi-threadsafe byte queue (multiple threads can use the putter functions at the same time, only one thread can use the getter functions (same thread for clear function), the getter thread and putter threads or other threads can all use length)
  class FASTMUSICPLAYER_EXPORT ConQueue {
	public:
		struct QBlk {
			QBlk *next;
			ByteArray data;
		};
	private:
		Mutex *last_lock;
		CondVar *last_cond;
		QBlk *last;
		QBlk *first;
		size_t total_bytes;
		// void chg_bytes(size_t amt, bool is_add = true);
	public:
		ConQueue();
		ByteArray get_bytes(size_t num_bytes);
		void get_bytes(ByteArray &into, size_t num_bytes, size_t at = 0);
		size_t try_get_bytes(ByteArray &into, size_t num_bytes, size_t at = 0);//Returns the position where it left off (NumBytesRead = Rtn - at and maxed at num_bytes)
		// ByteArray peek_bytes(size_t num_bytes);
		ByteArray try_get_bytes(size_t num_bytes);
		void put_bytes(const ByteArray &bytes);
		void put_bytes(ByteArray &&bytes);
		void clear(size_t num_bytes);
		size_t length();
		~ConQueue();

		// void *cb_obj;
		// void(*get_func)(void *obj, size_t num_bytes);
	};
}