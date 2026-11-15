#include "baseline/filter.hpp"
#include "baseline/statistics.hpp"
#include "baseline/sinkhorn.hpp"
#include "baseline/evaluation.hpp"
#include "baseline/time_series.hpp"
#include <iostream>
#include <stdexcept>
#include <cmath>
using namespace baseline;
// 不使用 assert，Release 构建中也必须实际执行检查
static void check(bool b,const char* msg){if(!b)throw std::runtime_error(msg);}
static void close(double a,double b,double tol,const char* msg){check(std::abs(a-b)<tol,msg);}
int main() {
    try {
        Model linear("linear"),gordon("gordon");FilterConfig c;
        close(gordon.transition(0,1),8,1e-12,"Gordon相位错误");
        auto kf=make_filter(linear,c,"kf",1);kf->predict(1);
        close(kf->estimate().variance,1.82,1e-12,"KF预测方差错误");
        kf->update(1);double mean=1.82/2.32,var=1.82*0.5/2.32;
        close(kf->estimate().mean,mean,1e-12,"KF增益错误");
        close(kf->estimate().variance,var,1e-12,"Joseph方差错误");
        for(auto a:{"bpf","enkf"}) {
            c.n=100000;auto f=make_filter(linear,c,a,177);f->predict(1);f->update(1);
            close(f->estimate().mean,mean,0.02,"线性高斯均值不匹配");
            close(f->estimate().variance,var,0.02,"线性高斯方差不匹配");
        }
        auto r=sinkhorn_transform({0,1},{0.5,0.5},0.4,1e-10,2000);
        double diag=0.5/(1+std::exp(-1/0.4));
        close(r.plan(0,0),diag,1e-9,"2x2解析耦合错误");
        check(r.diagnostics.converged==1,"简单Sinkhorn未收敛");
        for(double eps:{0.01,0.1,1.0,10.0}) {
            auto s=sinkhorn_transform({-10,-3,2,8},{0.7,0,0.2,0.1},eps,1e-8,2000);
            Eigen::Vector4d w;w<<0.7,0,0.2,0.1;
            check((s.plan.rowwise().sum()-w).lpNorm<1>()<1e-10,"源边缘错误");
            check((s.plan.colwise().sum().array()-0.25).abs().sum()<1e-10,"目标边缘错误");
            close(empirical(s.particles).mean,-5.8,1e-9,"ETPF均值未保持");
            check(empirical(s.particles).variance<=empirical({-10,-3,2,8},{0.7,0,0.2,0.1}).variance+1e-9,"重心方差不应增加");
        }
        auto short_ot=sinkhorn_transform({-3,0,2},{0.1,0.7,0.2},2,1e-14,1);
        check(short_ot.diagnostics.converged==0,"应记录未收敛");
        Record a,b;a.step=1;a.posterior={2,1,0,3};a.prior=a.posterior;
        b.step=2;b.observed=1;b.posterior={4,1,0,5};b.prior={3,1,0,5};
        auto m=evaluate({{1,1},{2,2}},{a,b},2);
        close(m.sse,5,1e-12,"RMSE平方误差汇总错误");
        close(m.pre_sse,1,1e-12,"更新前误差错误");
        // 手算序列区分逐时刻RMSE，累计RMSE以及平均绝对误差
        Record s1,s2,t1,t2;s1.step=t1.step=1;s2.step=t2.step=2;
        s2.observed=t2.observed=1;
        s1.posterior.mean=s1.prior.mean=0;t1.posterior.mean=t1.prior.mean=2;
        s2.posterior.mean=4;t2.posterior.mean=0;s2.prior.mean=3;t2.prior.mean=1;
        TimeSeriesAccumulator series;
        series.add({{1,0},{2,0}},{s1,s2});series.add({{1,0},{2,0}},{t1,t2});
        auto points=series.result();
        close(points[0].rmse,std::sqrt(2.0),1e-12,"时刻1 RMSE错误");
        close(points[1].rmse,std::sqrt(8.0),1e-12,"时刻2 RMSE错误");
        close(points[1].cumulative_rmse,std::sqrt(5.0),1e-12,"累计RMSE错误");
        close(points[1].prior_rmse,std::sqrt(5.0),1e-12,"时序预测RMSE错误");
        check(points[1].trials==2,"时序轨迹计数错误");
        bool mismatch=false;
        try { series.add({{1,0}},{s1}); }catch(...){mismatch=true;}
        check(mismatch,"应拒绝不同长度的轨迹");
        bool rejected=false;try{make_filter(gordon,c,"kf",1);}catch(...){rejected=true;}
        check(rejected,"非线性模型必须拒绝标准KF");
        std::cout<<"全部数学与接口检查通过\n";
    } catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
