#include "baseline/cli.hpp"
#include "baseline/filter.hpp"
#include "baseline/io.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
// 独立诊断入口，不修改正式filter二进制，粒子取各集合算法完成更新后的等权状态。
int main(int argc, char** argv) {
    try {
        using namespace baseline; Args args(argc, argv);
        auto data=read_observations(args.require("observations"));
        int target=args.integer("step",21); if(target<1 || target>static_cast<int>(data.size()))throw std::invalid_argument("快照时间步越界");
        FilterConfig config; config.n=args.integer("n",500);
        config.epsilon=args.real("epsilon",1);config.tolerance=args.real("tolerance",1e-8);
        config.max_iterations=args.integer("max-iterations",1000);
        std::string algorithm=args.get("algorithm","bpf");
        if(algorithm!="bpf"&&algorithm!="enkf"&&algorithm!="etpf")throw std::invalid_argument("快照只适用于三种集合算法");
        auto filter=make_filter(Model("gordon"),config,algorithm,args.seed());
        std::vector<Record> records;
        for(const auto& observation:data) {
            if(observation.step>target)break;
            Record record;record.step=observation.step;record.observed=1;
            filter->predict(record.step);record.prior=filter->estimate();
            filter->update(observation.value);record.posterior=filter->estimate();record.diagnostics=filter->diagnostics();
            records.push_back(record);
        }
        auto particles=filter->particles();std::ostringstream out;
        out<<std::setprecision(17)<<"step,index,x,weight\n";
        for(size_t i=0;i<particles.size();++i)out<<target<<','<<i<<','<<particles[i]<<','<<1.0/particles.size()<<'\n';
        auto directory=std::filesystem::path(args.require("output"));
        atomic_text(directory/"particles.csv",out.str());write_records(directory/"filter.csv",records);
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
