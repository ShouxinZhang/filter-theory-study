#include "pf/noise.hpp"
#include <iomanip>
#include <locale>
#include <sstream>

namespace pf {
std::string Noise::encode() const {
  // 固定区域设置与双精度往返精度, 使冻结描述不依赖机器语言设置。
  std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(17);
  out<<(kind_==NoiseKind::normal?"normal":"uniform")<<' '<<dimension();
  for(double v:first_)out<<' '<<v;
  for(double v:second_)out<<' '<<v;
  return out.str();
}
Noise Noise::decode(const std::string& description) {
  std::istringstream in(description);in.imbue(std::locale::classic());std::string kind;int dim=0;
  require(bool(in>>kind>>dim)&&dim>0&&dim<=1000000,"噪声描述类别或 dim 非法");
  require(kind=="normal"||kind=="uniform","未知噪声类别: "+kind);
  Vector first(dim),second(dim);
  for(double& v:first)require(bool(in>>v),"噪声第一参数数组不完整");
  for(double& v:second)require(bool(in>>v),"噪声第二参数数组不完整");
  in>>std::ws;require(in.eof(),"噪声描述含多余参数");
  return kind=="normal"?normal(std::move(first),std::move(second)):uniform(std::move(first),std::move(second));
}
} // namespace pf
