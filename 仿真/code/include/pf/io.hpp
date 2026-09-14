#pragma once
#include "pf/records.hpp"
#include <filesystem>
#include <fstream>

namespace pf {
namespace fs=std::filesystem;
// 二进制格式固定小端 uint64 / IEEE754 double, 字符串与矩阵均有长度前缀。
class Writer {
 public:
  explicit Writer(const fs::path& path);
  void integer(std::uint64_t value);
  void real(double value);
  void text(const std::string& value);
  void matrix(const Matrix& value);
  void close();
 private:
  std::ofstream file_;
};
class Reader {
 public:
  explicit Reader(const fs::path& path);
  std::uint64_t integer(std::uint64_t maximum=UINT64_MAX);
  double real();
  std::string text();
  Matrix matrix();
  Vector vector();
  void end();
 private:
  std::ifstream file_;
  std::uint64_t remaining_;
  void bytes(char* output, std::size_t count);
};
std::string sha256(const fs::path& path);
void verify_file(const fs::path& path);
void commit_file(const fs::path& temporary, const fs::path& destination);
void save_run(const fs::path& path,const RunRecord& run);
RunRecord load_run(const fs::path& path);
void save_reference(const fs::path& path,const ReferenceRecord& reference);
ReferenceRecord load_reference(const fs::path& path);
} // namespace pf
