#include "baseline/cli.hpp"
#include "baseline/filter.hpp"
#include "baseline/io.hpp"
#include <chrono>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <sys/resource.h>
// 读取和写出均在滤波内核计时之外，每步只向接口传递到达的观测
int main(int argc,char**argv) {
    try {
        using namespace baseline; using Clock=std::chrono::steady_clock;
        auto begin=Clock::now();Args a(argc,argv);Model model(a.get("model","gordon"));
        FilterConfig c;c.n=a.integer("n",500);c.epsilon=a.real("epsilon",1);
        c.tolerance=a.real("tolerance",1e-8);c.max_iterations=a.integer("max-iterations",2000);
        int interval=a.integer("interval",1);if(interval<1)throw std::invalid_argument("观测间隔必须为正");
        auto input=read_observations(a.require("observations"));
        auto f=make_filter(model,c,a.require("algorithm"),a.seed());
        std::vector<Record> rows;rows.reserve(input.size());std::ostringstream snapshots;
        bool snapshot=!a.get("snapshot").empty(); snapshots<<std::setprecision(17)<<"step,index,x\n";
        for(const auto& observation:input) {
            Record row;row.step=observation.step;row.observed=row.step%interval==0;
            auto t0=Clock::now();f->predict(row.step);row.prior=f->estimate();auto t1=Clock::now();
            if(row.observed)f->update(observation.value);
            row.posterior=f->estimate();row.diagnostics=f->diagnostics();auto t2=Clock::now();
            row.predict_us=std::chrono::duration<double,std::micro>(t1-t0).count();
            row.update_us=row.observed?std::chrono::duration<double,std::micro>(t2-t1).count():0;
            rows.push_back(row);
            if(snapshot && row.observed && row.step%8==0) {
                auto particles=f->particles();
                for(size_t i=0;i<particles.size();++i)snapshots<<row.step<<','<<i<<','<<particles[i]<<'\n';
            }
        }
        write_records(a.require("output"),rows);
        if(snapshot)atomic_text(a.get("snapshot"),snapshots.str());
        struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
        auto seconds=std::chrono::duration<double>(Clock::now()-begin).count();
        std::ostringstream meta;meta<<std::setprecision(17)<<"wall_seconds,peak_rss_kib\n"<<seconds<<','<<usage.ru_maxrss<<'\n';
        atomic_text(a.require("output")+".runtime.csv",meta.str());
    } catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
