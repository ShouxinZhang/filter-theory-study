#include "baseline/sinkhorn.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
namespace baseline {
using Matrix=Eigen::Matrix<double,Eigen::Dynamic,Eigen::Dynamic,Eigen::RowMajor>;
using Vector=Eigen::VectorXd;
TransportResult sinkhorn_transform(const std::vector<double>& x,const std::vector<double>& w,
                                  double eps,double tol,int limit) {
    int n=static_cast<int>(x.size());
    if(n<1 || w.size()!=x.size() || !(eps>0) || !(tol>0) || limit<1)
        throw std::invalid_argument("Sinkhorn 参数错误");
    double mass=std::accumulate(w.begin(),w.end(),0.0);
    if(std::abs(mass-1)>1e-9)throw std::invalid_argument("OT 权重必须归一化");
    std::vector<int> target(n),source;
    std::iota(target.begin(),target.end(),0);
    for(int i=0;i<n;++i) {
        if(w[i]<0||!std::isfinite(w[i])||!std::isfinite(x[i]))throw std::invalid_argument("OT 输入非有限");
        if(w[i]>0)source.push_back(i);
    }
    auto order=[&](int i,int j){return x[i]<x[j];};
    std::stable_sort(target.begin(),target.end(),order);std::stable_sort(source.begin(),source.end(),order);
    int m=static_cast<int>(source.size());
    Vector a(m),b=Vector::Constant(n,1.0/n), alpha=Vector::Zero(m),beta=Vector::Zero(n);
    Matrix cost(m,n),kernel(m,n);
    for(int i=0;i<m;++i) {
        a[i]=w[source[i]];
        for(int j=0;j<n;++j)cost(i,j)=std::pow(x[source[i]]-x[target[j]],2);
    }
    // 单调输运的阶梯支撑给出对偶可行势，避免小 epsilon 从严重下溢核开始
    int i=0,j=0; double ca=a[0],cb=b[0]; beta[0]=cost(0,0);
    while(i<m-1 || j<n-1) {
        if(i<m-1 && (j==n-1 || ca<=cb)) {++i;alpha[i]=cost(i,j)-beta[j];ca+=a[i];}
        else {++j;beta[j]=cost(i,j)-alpha[i];cb+=b[j];}
    }
    auto rebuild=[&] {
        for(int r=0;r<m;++r)for(int c=0;c<n;++c)
            kernel(r,c)=std::exp(std::min(700.0,(alpha[r]+beta[c]-cost(r,c))/eps));
    };
    rebuild(); Vector u=Vector::Ones(m),v=Vector::Ones(n),kv(m),ktu(n);
    Diagnostics diag; Matrix plan(m,n);
    for(int it=1;it<=limit;++it) {
        kv.noalias()=kernel*v;
        for(int r=0;r<m;++r)u[r]=a[r]/std::max(kv[r],1e-300);
        ktu.noalias()=kernel.transpose()*u;
        for(int c=0;c<n;++c)v[c]=b[c]/std::max(ktu[c],1e-300);
        if(!u.allFinite()||!v.allFinite())throw std::runtime_error("Sinkhorn 非有限缩放");
        // 吸收缩放量到对偶势，重新构造核，不修改 epsilon
        if(u.maxCoeff()>1e80 || v.maxCoeff()>1e80 || u.minCoeff()<1e-80 || v.minCoeff()<1e-80) {
            for(int r=0;r<m;++r)alpha[r]+=eps*std::log(std::max(u[r],1e-300));
            for(int c=0;c<n;++c)beta[c]+=eps*std::log(std::max(v[c],1e-300));
            rebuild();u.setOnes();v.setOnes();
        }
        if(it%10==0||it==limit||it==1) {
            kv.noalias()=kernel*v;ktu.noalias()=kernel.transpose()*u;
            diag.residual=(u.cwiseProduct(kv)-a).lpNorm<1>()+(v.cwiseProduct(ktu)-b).lpNorm<1>();
            diag.iterations=it;
            if(diag.residual<=tol)break;
        }
    }
    diag.converged=diag.residual<=tol?1:0;
    plan=kernel;
    for(int r=0;r<m;++r)plan.row(r)*=u[r];
    for(int c=0;c<n;++c)plan.col(c)*=v[c];
    if(!plan.allFinite())throw std::runtime_error("Sinkhorn 非有限耦合");
    // Altschuler 可行化：行列仅缩小，剩余质量以秩一补全，记录修正幅度
    Matrix before=plan;
    Vector rows=plan.rowwise().sum();
    for(int r=0;r<m;++r)if(rows[r]>0)plan.row(r)*=std::min(1.0,a[r]/rows[r]);
    Vector cols=plan.colwise().sum().transpose();
    for(int c=0;c<n;++c)if(cols[c]>0)plan.col(c)*=std::min(1.0,b[c]/cols[c]);
    Vector ra=(a-plan.rowwise().sum()).cwiseMax(0);
    Vector rb=(b-plan.colwise().sum().transpose()).cwiseMax(0);
    double remaining=ra.sum();
    if(remaining>1e-15 && rb.sum()>0)plan.noalias()+=ra*rb.transpose()/rb.sum();
    diag.correction=(plan-before).cwiseAbs().sum();
    diag.transport_cost=(plan.array()*cost.array()).sum();
    TransportResult result;result.particles.assign(n,0);result.plan=Matrix::Zero(n,n);
    for(int r=0;r<m;++r)for(int c=0;c<n;++c) {
        result.plan(source[r],target[c])=plan(r,c);
        result.particles[target[c]]+=n*plan(r,c)*x[source[r]];
    }
    double final_residual=(plan.rowwise().sum()-a).lpNorm<1>()+
                          (plan.colwise().sum().transpose()-b).lpNorm<1>();
    if(final_residual>1e-10)throw std::runtime_error("耦合可行化失败");
    result.diagnostics=diag;return result;
}
}
