#include "baseline/generator.hpp"
#include "baseline/random.hpp"
#include "baseline/io.hpp"
#include <cmath>
#include <sstream>
#include <iomanip>
#include <stdexcept>
namespace baseline {
void generate(const Model& m,int steps,uint64_t seed,const std::filesystem::path& obs,
              const std::filesystem::path& truth,bool fixed) {
    if(steps<1)throw std::invalid_argument("步数必须为正");
    if(std::filesystem::exists(obs)||std::filesystem::exists(truth))
        throw std::runtime_error("冻结数据不可覆盖");
    Random initial(split_seed(seed,1)), process(split_seed(seed,2)), measurement(split_seed(seed,3));
    double x=fixed?0.1:m.initial_mean+std::sqrt(m.initial_variance)*initial.gaussian();
    std::ostringstream o,t; o<<std::setprecision(17)<<"step,y\n"; t<<std::setprecision(17)<<"step,x\n";
    for(int k=1;k<=steps;++k) {
        x=m.transition(x,k)+std::sqrt(m.q)*process.gaussian();
        o<<k<<','<<m.observation(x)+std::sqrt(m.r)*measurement.gaussian()<<'\n';
        t<<k<<','<<x<<'\n';
    }
    atomic_text(obs,o.str()); atomic_text(truth,t.str());
}
}
