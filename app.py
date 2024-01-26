from flask import Flask
from flask import request
from flask import render_template
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from calendar import monthrange 

app = Flask(__name__)

# Başlangıç ve bitiş tarihleri
start_date = datetime(2024, 2, 1)
end_date = datetime(2025, 2, 1)

# Resmi tatiller ve süreleri
holidays = ["9/4", "23/4", "1/5", "19/5", "15/6", "15/7", "30/8", "29/10"]
holiday_duration = {"9/4": 3.5, "15/6": 4.5}

def create_holiday_dates(holidays, holiday_duration, year):
    holidays_dates = []
    for day in holidays:
        date = datetime.strptime(f"{day}/{year}", "%d/%m/%Y")
        holidays_dates.append(date)
        if day in holiday_duration:
            for additional_day in range(1, int(holiday_duration[day]) + 1):
                holidays_dates.append(date + timedelta(days=additional_day))
    return holidays_dates

# Modify the create_schedule function to compute monthly duty counts
def create_schedule(professionals, start_date, end_date, holidays):
    holidays_dates = create_holiday_dates(holidays, holiday_duration, start_date.year)
    full_date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days)]
    all_working_days = [date for date in full_date_list if date not in holidays_dates]
    
    # Initialize the duty count and last duty day for each prosecutor
    duty_counts = {pro: 0 for pro in professionals}
    last_duty = {pro: start_date - timedelta(days=3) for pro in professionals}  # So everyone is eligible at the start
    
    schedule = {day: {'İç Nöbet': None, 'Dış Nöbet': None} for day in all_working_days}
    
    # Initialize monthly duty counts
    monthly_duty_counts = {pro: defaultdict(int) for pro in professionals}
    
    for day in all_working_days:
        month_year = f"{day.month}/{day.year}"
        eligible_pros = [pro for pro in professionals if day > last_duty[pro] + timedelta(days=2)]
        least_duty_pros = sorted(eligible_pros, key=lambda x: duty_counts[x])
        
        for duty_type in ['İç Nöbet', 'Dış Nöbet']:
            eligible_pros = [pro for pro in professionals if day > last_duty[pro] + timedelta(days=2) and schedule[day]['İç Nöbet'] != pro]
            # Eğer iç nöbet atanmışsa, iç nöbeti tutan kişiyi dış nöbet için uygun olmayanlar listesinden çıkar
            if schedule[day]['İç Nöbet']:
                eligible_pros = [pro for pro in eligible_pros if pro != schedule[day]['İç Nöbet']]
            least_duty_pros = sorted(eligible_pros, key=lambda x: duty_counts[x])
            
            for pro in least_duty_pros:
                if schedule[day][duty_type] is None:
                    schedule[day][duty_type] = pro
                    last_duty[pro] = day
                    duty_counts[pro] += 1
                    monthly_duty_counts[pro][month_year] += 1
                    break

    return schedule, monthly_duty_counts

def create_monthly_duty_table(monthly_duty_counts):
    # Convert the monthly duty counts dictionary to a Pandas DataFrame
    df_monthly_duty = pd.DataFrame.from_dict(monthly_duty_counts, orient='index').fillna(0)
    
    # Reset the index and rename the columns
    df_monthly_duty = df_monthly_duty.reset_index()
    df_monthly_duty.rename(columns={'index': 'Person'}, inplace=True)
    
    # Convert the DataFrame to an HTML table with Bootstrap classes
    monthly_duty_table = df_monthly_duty.to_html(classes='table', index=False)
    
    return monthly_duty_table


def format_date(date):
    return date.strftime("%Y/%m/%d")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        prosecutors_A = request.form.getlist('prosecutorsA[]')
        prosecutors_B = request.form.getlist('prosecutorsB[]')

        schedule_A, monthly_duty_df_A = create_schedule(prosecutors_A, start_date, end_date, holidays)
        schedule_B, monthly_duty_df_B = create_schedule(prosecutors_B, start_date, end_date, holidays)

        df_schedule_A = pd.DataFrame(schedule_A).T.reset_index()
        df_schedule_B = pd.DataFrame(schedule_B).T.reset_index()

        df_schedule_A['index'] = df_schedule_A['index'].apply(format_date)
        df_schedule_B['index'] = df_schedule_B['index'].apply(format_date)

        df_schedule_A.rename(columns={'index': 'Tarih'}, inplace=True)
        df_schedule_B.rename(columns={'index': 'Tarih'}, inplace=True)
        
        # Aylık nöbet sayılarını içeren tabloyu oluştur
        # Create HTML tables for monthly duty counts
        monthly_duty_table_A = create_monthly_duty_table(monthly_duty_df_A)
        monthly_duty_table_B = create_monthly_duty_table(monthly_duty_df_B)


        return render_template('index.html', tables=[
            df_schedule_A.to_html(classes='table'), 
            df_schedule_B.to_html(classes='table'),
            monthly_duty_table_A,
            monthly_duty_table_B
            ], titles=['', 'Ankara A Nöbet Listesi', 'Ankara B Nöbet Listesi', 'Ankara A Aylık Nöbet', 'Ankara B Aylık Nöbet'])
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
