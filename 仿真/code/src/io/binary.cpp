#include "pf/io.hpp"
#include <openssl/evp.h>
#include <array>
#include <bit>
#include <iomanip>
#include <sstream>

namespace pf {
static_assert(sizeof(double)==8 && std::numeric_limits<double>::is_iec559,"二进制格式要求 IEEE754 binary64");
Writer::Writer(const fs::path& path):file_(path,std::ios::binary|std::ios::trunc) {
  require(bool(file_),"无法创建文件: "+path.string());
  file_.exceptions(std::ios::badbit|std::ios::failbit);
}
void Writer::integer(std::uint64_t v) {
  char bytes[8];
  for (int i=0;i<8;++i) bytes[i]=static_cast<char>((v>>(8*i))&255);
  file_.write(bytes,8);
}
void Writer::real(double v) { integer(std::bit_cast<std::uint64_t>(v)); }
void Writer::text(const std::string& value) {
  integer(value.size());file_.write(value.data(),static_cast<std::streamsize>(value.size()));
}
void Writer::matrix(const Matrix& value) {
  integer(value.rows());integer(value.cols());
  for (Eigen::Index i=0;i<value.size();++i) real(value.data()[i]);
}
void Writer::close() { file_.close(); }
Reader::Reader(const fs::path& path):file_(path,std::ios::binary),remaining_(fs::file_size(path)) {
  require(bool(file_),"无法读取文件: "+path.string());
}
void Reader::bytes(char* output,std::size_t count) {
  require(count<=remaining_,"文件截断或长度字段非法");
  file_.read(output,static_cast<std::streamsize>(count));
  require(bool(file_),"文件读取失败");remaining_-=count;
}
std::uint64_t Reader::integer(std::uint64_t maximum) {
  std::array<unsigned char,8> b{};bytes(reinterpret_cast<char*>(b.data()),8);
  std::uint64_t value=0;
  for (int i=0;i<8;++i) value|=std::uint64_t(b[i])<<(8*i);
  require(value<=maximum,"文件数值超过允许范围");return value;
}
double Reader::real() { return std::bit_cast<double>(integer()); }
std::string Reader::text() {
  std::string value(integer(1048576),'\0');bytes(value.data(),value.size());return value;
}
Matrix Reader::matrix() {
  const auto rows=integer(10000000),cols=integer(10000000);
  require(rows==0 || cols<=remaining_/8/rows,"矩阵长度超过文件内容");
  Matrix value(rows,cols);
  for (Eigen::Index i=0;i<value.size();++i) value.data()[i]=real();
  return value;
}
Vector Reader::vector() { Matrix value=matrix();require(value.cols()==1,"文件中的向量列数错误");return value.col(0); }
void Reader::end() { require(remaining_==0,"文件含额外尾部数据"); }
std::string sha256(const fs::path& path) {
  std::ifstream input(path,std::ios::binary);require(bool(input),"无法计算文件摘要");
  EVP_MD_CTX* context=EVP_MD_CTX_new();require(context!=nullptr,"SHA-256 初始化失败");
  EVP_DigestInit_ex(context,EVP_sha256(),nullptr);
  std::array<char,65536> buffer{};
  while(input) { input.read(buffer.data(),buffer.size());EVP_DigestUpdate(context,buffer.data(),input.gcount()); }
  require(input.eof(),"摘要读取失败");
  unsigned char digest[EVP_MAX_MD_SIZE];unsigned int length=0;
  EVP_DigestFinal_ex(context,digest,&length);EVP_MD_CTX_free(context);
  std::ostringstream output;output<<std::hex<<std::setfill('0');
  for(unsigned int i=0;i<length;++i) output<<std::setw(2)<<static_cast<unsigned int>(digest[i]);
  return output.str();
}
void verify_file(const fs::path& path) {
  std::ifstream sidecar(path.string()+".sha256");std::string expected;sidecar>>expected;
  require(expected.size()==64 && expected==sha256(path),"SHA-256 不匹配或检查点未完成: "+path.string());
}
void commit_file(const fs::path& temporary,const fs::path& destination) {
  require(!fs::exists(destination),"拒绝覆盖已有文件: "+destination.string());
  const auto digest=sha256(temporary);
  const fs::path side=destination.string()+".sha256.partial";
  { std::ofstream out(side);out<<digest<<'\n';out.close();require(bool(out),"写入摘要失败"); }
  fs::rename(temporary,destination);
  fs::rename(side,destination.string()+".sha256"); // 摘要存在意味着该轨迹检查点完成。
}
} // namespace pf
