
class TaxRateInfo:
    def __init__(self, level, rate):
        self.level = level
        self.rate = rate

taxrateMap = [ TaxRateInfo(5, 0.05),
               TaxRateInfo(5, 0.1),
               TaxRateInfo(8, 0.15),
               TaxRateInfo(14, 0.2),
               TaxRateInfo(20, 0.25),
               TaxRateInfo(28, 0.3)
               ]
insuranceRate = 0.105
def taxof(salary, selfAbatement = 9.0, dependentAbatement = 0, dependentCount = 0):
    afterAbatement = salary - selfAbatement - dependentCount * dependentAbatement
    tax = 0.0
    if afterAbatement > 0:
        for taxRateInfo in taxrateMap:
            if afterAbatement > taxRateInfo.level:
                tax += taxRateInfo.level * taxRateInfo.rate
                afterAbatement -= taxRateInfo.level
            else:
                tax += afterAbatement * taxRateInfo.rate
                afterAbatement = 0
                break

        if afterAbatement > 0:
            tax += afterAbatement * 0.35

    return tax

def totalIncome(salary, selfAbatement = 9.0, dependentAbatement = 3.6, dependentCount = 2):
    salary -= insuranceRate * salary
    salary -= taxof(salary, selfAbatement, dependentAbatement, dependentCount)
    return salary

if __name__ == "__main__":
    print(totalIncome(50.9))