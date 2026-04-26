from flask import Flask, render_template, request, flash, redirect, url_for
import re

app = Flask(__name__)
app.secret_key = 'sahabat_mmu_secret'

# Utility to check for MMU student email 
def is_mmu_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@mmu\.edu\.my$", email))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if not is_mmu_email(email):
            flash("Please use your official MMU student email.")
            return redirect(url_for('register'))
        # Logic to save user to database goes here
        return "Registration successful!"
    return render_template('register.html')

@app.route('/discovery')
def discovery():
    # Example logic for "Halal-by-Design" filtering [cite: 64, 66]
    # You would typically filter users by gender or common interests here
    return render_template('discovery.html')

if __name__ == '__main__':
    app.run(debug=True)