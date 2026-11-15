#include "baseline/cli.hpp"
#include "baseline/io.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <sstream>
// 论文统计独立于滤波器，读取冻结真值，既有指标和串行内核计时。
int main(int argc, char** argv) {
    try {
        using namespace baseline; Args args(argc,argv); std::string line;
        std::ifstream truths(args.require("truth-index")); double truth2=0; size_t count=0;
        if(!std::getline(truths,line)||line!="truth_path")throw std::runtime_error("真值索引错误");
        while(std::getline(truths,line))for(auto r:read_truth(line)){truth2+=r.value*r.value;++count;}
        if(!count||truth2<=0)throw std::runtime_error("真值尺度不合法");
        const double scale=std::sqrt(truth2/count);
        std::ifstream summary(args.require("summary")); std::getline(summary,line);
        auto header=split(line);std::map<std::string,size_t> col;for(size_t i=0;i<header.size();++i)col[header[i]]=i;
        std::ostringstream accuracy;accuracy<<std::setprecision(17)
            <<"config_id,algorithm,n,epsilon,interval,rmse,ci_low,ci_high,nrmse_percent,truth_rms,ot_nonconverged_percent\n";
        while(std::getline(summary,line)){
            auto row=split(line);auto get=[&](const std::string& key){return row.at(col.at(key));};
            accuracy<<get("config_id")<<','<<get("algorithm")<<','<<get("n")<<','<<get("epsilon")<<','<<get("interval")<<','
                <<get("rmse")<<','<<get("ci_low")<<','<<get("ci_high")<<','<<100*std::stod(get("rmse"))/scale<<','<<scale<<','
                <<100*std::stod(get("ot_nonconverged_fraction"))<<'\n';
        }
        atomic_text(std::filesystem::path(args.require("output"))/"accuracy.csv",accuracy.str());
        std::ifstream timing(args.require("timing-index"));
        if(!std::getline(timing,line)||line!="config_id,algorithm,n,trial,repeat,filter_path")throw std::runtime_error("计时索引错误");
        struct Group{std::string algorithm,n;std::map<int,std::vector<double>> total,update;};
        std::map<std::string,Group> groups;
        while(std::getline(timing,line)){
            auto row=split(line);auto records=read_records(row.at(5));if(records.empty())throw std::runtime_error("计时为空");
            double prediction=0,update=0,observed=0;
            for(auto r:records){prediction+=r.predict_us;update+=r.update_us;observed+=r.observed;}
            auto&g=groups[row[0]];g.algorithm=row[1];g.n=row[2];int trial=std::stoi(row[3]);
            g.total[trial].push_back((prediction+update)/records.size());
            g.update[trial].push_back(update/observed);
        }
        auto aggregate=[](const std::map<int,std::vector<double>>& input){
            std::vector<double> medians;
            for(auto [trial,repeats]:input){
                if(repeats.size()!=3)throw std::runtime_error("每条轨迹需要三次重复");
                std::sort(repeats.begin(),repeats.end());medians.push_back(repeats[1]);
            }
            double mean=std::accumulate(medians.begin(),medians.end(),0.0)/medians.size(),variance=0;
            for(double v:medians)variance+=(v-mean)*(v-mean);
            return std::pair<double,double>{mean,std::sqrt(variance/(medians.size()-1))};
        };
        std::ostringstream times;times<<std::setprecision(17)<<"config_id,algorithm,n,trials,repeats,step_us_mean,step_us_sd,update_us_mean,update_us_sd\n";
        for(auto&[id,g]:groups){auto total=aggregate(g.total),update=aggregate(g.update);
            times<<id<<','<<g.algorithm<<','<<g.n<<','<<g.total.size()<<",3,"<<total.first<<','<<total.second<<','<<update.first<<','<<update.second<<'\n';}
        atomic_text(std::filesystem::path(args.require("output"))/"runtime.csv",times.str());
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
