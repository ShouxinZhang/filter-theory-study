#include "baseline/cli.hpp"
#include "baseline/density.hpp"
#include "baseline/io.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
// 密度评价和粒子递推分离，只读粒子快照与EKF既有后验矩。
int main(int argc, char** argv) {
    try {
        using namespace baseline; Args args(argc,argv);int step=args.integer("step",21);
        std::ifstream input(args.require("particles"));std::string line;
        if(!std::getline(input,line)||line!="step,index,x,weight")throw std::runtime_error("粒子快照表头错误");
        std::vector<double> particles,weights;
        while(std::getline(input,line)) {
            auto values=split(line);
            if(values.size()!=4||std::stoi(values[0])!=step)throw std::runtime_error("粒子快照格式错误");
            particles.push_back(std::stod(values[2]));weights.push_back(std::stod(values[3]));
        }
        GaussianKde kde(particles);
        for(double weight:weights)if(std::abs(weight-1.0/weights.size())>1e-12)throw std::runtime_error("此KDE入口只接受等权粒子");
        auto records=read_records(args.require("ekf"));
        if(step<1||step>static_cast<int>(records.size()))throw std::runtime_error("EKF时间步越界");
        auto gaussian=records[step-1].posterior;
        const double sigma=std::sqrt(gaussian.variance);
        double left=std::min(*std::min_element(particles.begin(),particles.end())-6*kde.bandwidth,gaussian.mean-6*sigma);
        double right=std::max(*std::max_element(particles.begin(),particles.end())+6*kde.bandwidth,gaussian.mean+6*sigma);
        const int points=2001;double dx=(right-left)/(points-1),integral_kde=0,integral_ekf=0;
        std::ostringstream grid;grid<<std::setprecision(17)<<"x,kde,ekf_gaussian\n";
        for(int i=0;i<points;++i){
            double x=left+i*dx,a=kde.density(x),b=gaussian_density(x,gaussian.mean,gaussian.variance);
            grid<<x<<','<<a<<','<<b<<'\n';double coefficient=(i==0||i==points-1)?0.5:1;
            integral_kde+=coefficient*dx*a;integral_ekf+=coefficient*dx*b;
        }
        if(std::abs(integral_kde-1)>1e-6||std::abs(integral_ekf-1)>1e-6)throw std::runtime_error("显示网格密度积分未通过检查");
        std::ostringstream meta;meta<<std::setprecision(17)<<"step,n,bandwidth,sample_mean,sample_variance,ekf_mean,ekf_variance,kde_integral,ekf_integral\n"
            <<step<<','<<particles.size()<<','<<kde.bandwidth<<','<<kde.sample_mean<<','<<kde.sample_variance<<','
            <<gaussian.mean<<','<<gaussian.variance<<','<<integral_kde<<','<<integral_ekf<<'\n';
        auto output=std::filesystem::path(args.require("output"));atomic_text(output/"density.csv",grid.str());atomic_text(output/"metadata.csv",meta.str());
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
