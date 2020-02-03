#include <stdint.h>

#if defined(_M_X64) || defined(_M_AMD64) || defined(__amd64__) || defined(__amd64)\
	|| defined(__x86_64__) || defined(__x86_64) || defined(__aarch64__)
	#define MAX_INT 0xFFFFFFFFFFFFFFFF
	#define MAX_HEX_DIGIT 16
#else
	#define MAX_INT 0xFFFFFFFF
	#define MAX_HEX_DIGIT 8
#endif

namespace fmp {
  template<typename T>
	class Array{
	private:
		size_t alloc_size;
		T * data;
	public:
		Array();
		Array(Array<T> &&copy);
		Array(const T *str_in, size_t len);
		Array(const Array<T> &copy);
		Array(const T ch_fill, const size_t len);
		Array(const Array<T> &copy, size_t len);
		~Array();
		void take(T *str_in, size_t len);
		void give(T *&str_out, size_t &len);
    void give();
		void swap(Array<T> &other);
		void add_missing(const Array<T> &other);
		void add_missing(const Array<T> &other, size_t until);
		void remove_from_start(size_t num_remove);
		void insert_at_start(size_t num_add);
		void insert_at_start(size_t num_add, T value);
		void write_from_at(const Array<T> &from, size_t begin = 0, size_t end = MAX_INT);
		Array<T> sub_array(size_t start, size_t stop = MAX_INT, ptrdiff_t step = 0) const;
		void set_length(size_t len);
		bool operator==(const Array<T> &compare) const;
		bool operator!=(const Array<T> &compare) const;
		Array<T> operator+(const Array<T> &add) const;
		Array<T> operator+(const T &add) const;
		T operator[](const size_t pos) const;
		Array<T> &operator=(Array<T> &&copy);
		Array<T> &operator=(const Array<T> &copy);
		Array<T> &operator+=(const Array<T> &add);
		Array<T> &operator+=(const T &add);
		//less cpu intensive for higher performance. NOTE: do NOT deallocate or the Array object becomes invalid
		T *get_data() const;
		bool insert(size_t pos, T value);
		bool remove(size_t pos);
		T &operator[](const size_t pos);
		bool contains(const T &value) const;
		bool find(size_t &pos, T value, bool pos_is_start = false);
		bool rfind(size_t &pos, T value, bool pos_is_start = false);
		size_t length() const;
		T &at_end();
		const T at_end() const;
		Array<T> &operator*=(size_t num);
		Array<T> operator*(size_t num) const;
		T *begin();
		T *end();
		//friend class ReprArray;
	};
  template<typename T>
  void swap(T &a, T &b) {
    T Tmp = (T &&)a;
    a = (T &&)b;
    b = (T &&)Tmp;
  }
  template<typename T>
	Array<T>::Array(){
		data = 0;
		alloc_size = 0;
	}

	template<typename T>
	Array<T>::Array(Array<T> &&copy){
		data = copy.data;
		copy.data = 0;
		alloc_size = copy.alloc_size;
		copy.alloc_size = 0;
	}

	template<typename T>
	Array<T>::Array(const T *copy, size_t len){
		alloc_size = len;
		data = new T[alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			data[i] = copy[i];
			++i;
		}
	}

	template<typename T>
	Array<T>::Array(const Array<T> &copy){
		alloc_size = copy.alloc_size;
		data = new T[alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			data[i] = copy.data[i];
			++i;
		}
	}

	template<typename T>
	Array<T>::Array(const T ch_fill, const size_t len){
		alloc_size = len;
		data = new T[alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			data[i] = ch_fill;
			++i;
		}
	}

	template<typename T>
	Array<T>::Array(const Array<T> &copy, size_t len){
		alloc_size = (len < copy.alloc_size) ? len : copy.alloc_size;
		data = new T[alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			data[i] = copy.data[i];
			++i;
		}
	}

	template<typename T>
	Array<T>::~Array(){
		if (alloc_size > 0) delete[] data;
	}

	template<typename T>
	void Array<T>::take(T *str_in, size_t len) {
		data = str_in;
		alloc_size = len;
	}

	template<typename T>
	void Array<T>::give(T *&str_out, size_t &len) {
		str_out = data;
		len = alloc_size;
		data = 0;
		alloc_size = 0;
	}

	template<typename T>
	void Array<T>::give() {
		data = 0;
		alloc_size = 0;
	}

	template<typename T>
	void Array<T>::swap(Array<T> &other){
		T *tmp_data = data;
		size_t tmp_len = alloc_size;
		alloc_size = other.alloc_size;
		data = other.data;
		other.alloc_size = tmp_len;
		other.data = tmp_data;
	}
	template<typename T>
	void Array<T>::set_length(size_t len){
		if (alloc_size == len) return;
		T *new_data = new T[len];
		for (size_t i = 0; (i < len) && (i < alloc_size); ++i){
			new_data[i] = data[i];
		}
		delete[] data;
		data = new_data;
		alloc_size = len;
	}

	template<typename T>
	void Array<T>::add_missing(const Array<T> &other){
		if (other.alloc_size <= alloc_size) return;
		T * new_data = new T[other.alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		while (i < other.alloc_size){
			new_data[i] = other.data[i];
			++i;
		}
		delete[] data;
		data = new_data;
		alloc_size = other.alloc_size;
	}
	template<typename T>
	void Array<T>::add_missing(const Array<T> &other, size_t until){
		if (until <= alloc_size) return;
		until = (until < other.alloc_size) ? until : other.alloc_size;
		T * new_data = new T[until];
		size_t i = 0;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		alloc_size = until;
		while (i < alloc_size){
			new_data[i] = other.data[i];
			++i;
		}
		delete[] data;
		data = new_data;
	}
	template<typename T>
	void Array<T>::remove_from_start(size_t num_remove){
		size_t i = 0, until = alloc_size - num_remove;
		T * new_data = new T[until];
		data += num_remove;
		while (i < until){
			new_data[i] = (T &&)data[i];
			++i;
		}
		data -= num_remove;
		delete[] data;
		data = new_data;
		alloc_size = until;
	}
	template<typename T>
	void Array<T>::insert_at_start(size_t num_add){
		if (num_add == 0) return;
		T * new_data = new T[alloc_size + num_add];
		size_t i = 0;
		new_data += num_add;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		delete[] data;
		new_data -= num_add;
		alloc_size += num_add;
		data = new_data;
	}
	template<typename T>
	void Array<T>::insert_at_start(size_t num_add, T value){
		if (num_add == 0) return;
		T * new_data = new T[alloc_size + num_add];
		size_t i = 0;
		new_data += num_add;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		delete[] data;
		new_data -= num_add;
		i = 0;
		while (i < num_add){
			new_data[i] = value;
			++i;
		}
		alloc_size += num_add;
		data = new_data;
	}
	template<typename T>
	void Array<T>::write_from_at(const Array<T> &from, size_t begin, size_t end) {
		if (end - begin > from.alloc_size) end = begin + from.alloc_size;
		if (end > alloc_size) end = alloc_size;
		data += begin;
		end -= begin;
		for (size_t i = 0; i < end; ++i) {
			data[i] = from.data[i];
		}
		data -= begin;
	}
	template<typename T>
	Array<T> Array<T>::sub_array(size_t start, size_t stop, ptrdiff_t step) const {
		if (alloc_size == 0) return Array<T>();
		if ((stop > alloc_size) && stop != MAX_INT) stop = alloc_size;
		if (start > alloc_size) start = alloc_size - 1;
		if (step < 0)
		{
			bool StopMax = false;
			if (start >= alloc_size) start = alloc_size - 1;
			if (stop == MAX_INT)
			{
				stop = 0;
				StopMax = true;
			}
			else if (start <= stop) return Array<T>();
			size_t Range = start - stop;
			size_t Step0 = -step;
			Array<T> rtn;
			rtn.set_length(((start - stop) + (StopMax ? Step0 : Step0 - 1)) / Step0);
			size_t i = 0;
			for (T &Ch : rtn) {
				Ch = data[start - i * Step0];
				++i;
			}
			return rtn;
		}
		else
		{
			if (stop > alloc_size) stop = alloc_size;
			if (start >= stop) return Array<T>();
			size_t Step1 = step + 1;
			size_t c1 = 0;
			Array<T> rtn;
			rtn.set_length((stop - start - 1) / Step1 + 1);
			for (size_t i = 0; i < stop; i += Step1, ++c1) {
				rtn[c1] = data[i];
			}
			return rtn;
		}
	}

	template<typename T>
	bool Array<T>::operator==(const Array<T> &compare) const{
		if (alloc_size != compare.alloc_size) return false;
		size_t i = 0;
		while (i < alloc_size){
			if (data[i] != compare.data[i]) return false;
			++i;
		}
		return true;
	}

	template<typename T>
	bool Array<T>::operator!=(const Array<T> &compare) const{
		if (alloc_size != compare.alloc_size) return true;
		size_t i = 0;
		while (i < alloc_size){
			if (data[i] != compare.data[i]) return true;
			++i;
		}
		return false;
	}

	template<typename T>
	Array<T> Array<T>::operator+(const Array<T> &add) const{
		Array<T> rtn;
		rtn.alloc_size = alloc_size + add.alloc_size;
		rtn.data = new T[rtn.alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			rtn.data[i] = data[i];
			++i;
		}
		while (i < rtn.alloc_size){
			rtn.data[i] = add.data[i - alloc_size];
			++i;
		}
		return rtn;
	}

	template<typename T>
	Array<T> Array<T>::operator+(const T &add) const{
		Array<T> rtn;
		rtn.alloc_size = alloc_size + 1;
		rtn.data = new T[rtn.alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			rtn.data[i] = data[i];
			++i;
		}
		rtn.data[i] = add;
		return rtn;
	}

	template<typename T>
	T Array<T>::operator[](const size_t pos) const{
		if (pos >= alloc_size) return T();
		return data[pos];
	}

	template<typename T>
	Array<T> &Array<T>::operator=(Array<T> &&copy){
		if (alloc_size > 0) delete[] data;
		data = copy.data;
		copy.data = 0;
		alloc_size = copy.alloc_size;
		copy.alloc_size = 0;
		return (*this);
	}

	template<typename T>
	Array<T> &Array<T>::operator=(const Array<T> &copy){
		if (alloc_size > 0) delete[] data;
		alloc_size = copy.alloc_size;
		data = new T[alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			data[i] = copy.data[i];
			++i;
		}
		return (*this);
	}

	template<typename T>
	Array<T> &Array<T>::operator+=(const Array<T> &add){
		T *new_data = new T[alloc_size + add.alloc_size];
		size_t i = 0;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		if (alloc_size > 0) delete[] data;
		new_data += alloc_size;
		i = 0;
		while (i < add.alloc_size){
			new_data[i] = add.data[i];
			++i;
		}
		new_data -= alloc_size;
		alloc_size += add.alloc_size;
		data = new_data;
		return (*this);
	}

	template<typename T>
	Array<T> &Array<T>::operator+=(const T &add){
		T *new_data = new T[alloc_size + 1];
		size_t i = 0;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i];
			++i;
		}
		if (alloc_size > 0) delete[] data;
		new_data[i] = add;
		data = new_data;
		++alloc_size;
		return (*this);
	}

	//less cpu intensive for higher performance. NOTE: do NOT deallocate or the string object becomes invalid
	template<typename T>
	T *Array<T>::get_data() const{
		return data;
	}

	template<typename T>
	bool Array<T>::insert(size_t pos, T value){
		if (pos > alloc_size) return false;
		T *new_data = new T[alloc_size + 1];
		++alloc_size;
		size_t i = 0;
		while (i < pos){
			new_data[i] = (T &&)data[i];
			++i;
		}
		new_data[i] = value;
		++i;
		while (i < alloc_size){
			new_data[i] = (T &&)data[i - 1];
			++i;
		}
		delete[] data;
		data = new_data;
		return true;
	}

	template<typename T>
	bool Array<T>::remove(size_t pos){
		if (pos >= alloc_size) return false;
		T *new_data = new T[alloc_size - 1];
		--alloc_size;
		size_t i = 0;
		while (i < pos){
			new_data[i] = (T &&)data[i];
			++i;
		}
		while (i < alloc_size){
			new_data[i] = (T &&)data[i + 1];
			++i;
		}
		delete[] data;
		data = new_data;
		return true;
	}

	template<typename T>
	T &Array<T>::operator[](const size_t pos){
		return data[pos];
	}

	template<typename T>
	bool Array<T>::contains(const T &value) const {
		for (size_t i = 0; i < alloc_size; ++i) if (data[i] == value) return true;
		return false;
	}

	template<typename T>
	bool Array<T>::find(size_t &pos, T value, bool pos_is_start){
		for (size_t i = pos_is_start ? pos : 0; i < alloc_size; ++i){
			if (data[i] == value)
			{
				pos = i;
				return true;
			}
		}
		return false;
	}
	template<typename T>
	bool Array<T>::rfind(size_t &pos, T value, bool pos_is_start){
		--data;//to shift data so that (Old)data[0] is the same as (New)data[1]
		size_t until = pos_is_start ? pos : 0;
		for (size_t i = alloc_size; i > until; --i){
			if (data[i] == value)
			{
				pos = i;
				++data;
				return true;
			}
		}
		++data;
		return false;
	}
	template<typename T>
	size_t Array<T>::length() const{
		return alloc_size;
	}

	template<typename T>
	T &Array<T>::at_end(){
		return data[alloc_size - 1];
	}

	template<typename T>
	const T Array<T>::at_end() const{
		return data[alloc_size - 1];
	}

	template<typename T>
	Array<T> &Array<T>::operator*=(size_t num){
		T *new_data = new T[num * alloc_size];
		size_t i = 0;
		while (i < num){
			size_t c1 = 0;
			while (c1 < alloc_size){
				new_data[(i * alloc_size) + c1] = data[c1];
				++c1;
			}
			++i;
		}
		delete[] data;
		data = new_data;
		alloc_size *= num;
		return (*this);
	}

	template<typename T>
	Array<T> Array<T>::operator*(size_t num) const{
		Array<T> rtn;
		rtn.data = new T[num * alloc_size];
		size_t i = 0;
		while (i < num){
			size_t c1 = 0;
			while (c1 < alloc_size){
				rtn.data[(i * alloc_size) + c1] = data[c1];
				++c1;
			}
			++i;
		}
		rtn.alloc_size = num * alloc_size;
		return rtn;
	}
	template<typename T>
	T *Array<T>::begin(){
		return this->data;
	}
	template<typename T>
	T *Array<T>::end(){
		return this->data + this->alloc_size;
	}
  typedef Array<uint8_t> ByteArray;
}